import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.analysis_session import AnalysisSession

logger = logging.getLogger("fetalai.session_service")


class SessionService:
    """
    Manages analysis session lifecycle, state transitions, idempotency,
    and stale processing session recovery.
    """

    def create_or_get_session(
        self,
        db: Session,
        patient_id: Optional[str] = None,
        created_by_user_id: Optional[int] = None,
        idempotency_key: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Tuple[AnalysisSession, bool]:
        """
        Returns (session, was_created).
        If idempotency_key is provided and an existing session matches, returns it.
        Otherwise creates a new session in 'ready' state.
        """
        if idempotency_key:
            norm_key = idempotency_key.strip()
            existing = db.scalar(
                select(AnalysisSession).where(
                    AnalysisSession.idempotency_key == norm_key,
                    AnalysisSession.created_by == created_by_user_id,
                )
            )
            if existing is not None:
                logger.info(
                    "Idempotent hit for key '%s' -> returning existing session %s (%s)",
                    norm_key,
                    existing.session_id,
                    existing.status,
                )
                try:
                    from app.core.metrics import metrics_collector
                    from app.core.observability_logger import emit_structured_log
                    metrics_collector.record_idempotent_hit()
                    emit_structured_log(
                        "INFO",
                        "SESSION_IDEMPOTENT_HIT",
                        f"Idempotent hit for session {existing.session_id}",
                        details={"session_id": existing.session_id, "status": existing.status},
                    )
                except Exception:
                    pass
                return existing, False

        resolved_session_id = session_id.strip() if session_id and session_id.strip() else f"sess_{uuid.uuid4().hex[:12]}"
        
        session = AnalysisSession(
            session_id=resolved_session_id,
            patient_id=patient_id.strip() if patient_id else None,
            created_by=created_by_user_id,
            status="ready",
            idempotency_key=idempotency_key.strip() if idempotency_key else None,
            requested_models=[],
            completed_models=[],
            failed_models=[],
            summary_json={},
            result_json={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(
            "Created analysis session %s (id=%d, user_id=%s)",
            session.session_id,
            session.id,
            created_by_user_id,
        )
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_session_transition("ready")
        except Exception:
            pass
        return session, True

    def start_session_processing(
        self,
        session: AnalysisSession,
        requested_models: List[str],
        db: Session,
    ) -> AnalysisSession:
        """
        Transitions session status to 'processing' and records start timestamp.
        """
        session.status = "processing"
        session.requested_models = requested_models
        session.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        logger.info("Session %s transitioned to PROCESSING", session.session_id)
        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            metrics_collector.record_session_transition("processing")
            emit_structured_log(
                "INFO",
                "SESSION_PROCESSING",
                f"Session {session.session_id} processing started",
                details={"session_id": session.session_id, "status": "processing"},
            )
        except Exception:
            pass
        return session

    def complete_session(
        self,
        session: AnalysisSession,
        status: str,
        summary: Dict[str, Any],
        result: Dict[str, Any],
        completed_models: List[str],
        failed_models: List[str],
        db: Session,
        error_message: Optional[str] = None,
    ) -> AnalysisSession:
        """
        Stores analysis results, summary metrics, and transitions status
        to 'completed', 'partial', or 'failed'.
        """
        session.status = status
        session.summary_json = summary
        session.result_json = result
        session.completed_models = completed_models
        session.failed_models = failed_models
        session.completed_at = datetime.now(timezone.utc)
        session.error_message = error_message
        db.commit()
        db.refresh(session)
        logger.info("Session %s transitioned to %s", session.session_id, status.upper())
        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            metrics_collector.record_session_transition(status)
            emit_structured_log(
                "INFO",
                "SESSION_COMPLETED",
                f"Session {session.session_id} finished ({status})",
                details={"session_id": session.session_id, "status": status},
            )
        except Exception:
            pass
        return session

    def mark_interrupted(
        self,
        session: AnalysisSession,
        reason: str,
        db: Session,
    ) -> AnalysisSession:
        """
        Transitions a stuck or aborted session to 'interrupted'.
        """
        session.status = "interrupted"
        session.error_message = reason
        db.commit()
        db.refresh(session)
        logger.warning("Session %s marked INTERRUPTED: %s", session.session_id, reason)
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_session_transition("interrupted")
        except Exception:
            pass
        return session

    def get_session(
        self,
        identifier: str | int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> Optional[AnalysisSession]:
        """
        Fetches session by numeric ID or session_id with strict user authorization check.
        - Authenticated user: can access own sessions and unassigned sessions.
        - Anonymous user: can ONLY access unassigned sessions (created_by is None).
        """
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            num_id = int(identifier)
            stmt = select(AnalysisSession).where(AnalysisSession.id == num_id)
        else:
            ident_str = str(identifier).strip()
            stmt = select(AnalysisSession).where(AnalysisSession.session_id == ident_str)

        if user_id is not None:
            stmt = stmt.where(
                or_(
                    AnalysisSession.created_by == user_id,
                    AnalysisSession.created_by.is_(None),
                )
            )
        else:
            stmt = stmt.where(AnalysisSession.created_by.is_(None))

        return db.scalar(stmt)

    def list_sessions(
        self,
        db: Session,
        user_id: Optional[int] = None,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AnalysisSession], int]:
        """
        Returns a paginated list of sessions for the user with total count.
        """
        stmt = select(AnalysisSession)

        if user_id is not None:
            stmt = stmt.where(
                or_(
                    AnalysisSession.created_by == user_id,
                    AnalysisSession.created_by.is_(None),
                )
            )
        else:
            stmt = stmt.where(AnalysisSession.created_by.is_(None))

        if patient_id:
            stmt = stmt.where(AnalysisSession.patient_id == patient_id.strip())

        if status:
            stmt = stmt.where(AnalysisSession.status == status.strip().lower())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(AnalysisSession.created_at.desc())
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).all())
        return items, total

    def recover_stale_sessions(self, db: Session) -> int:
        """
        Sweeps any sessions that were left in 'processing' state during an unexpected
        process restart, marking them as 'interrupted'.
        """
        stale_sessions = list(
            db.scalars(
                select(AnalysisSession).where(AnalysisSession.status == "processing")
            ).all()
        )
        count = len(stale_sessions)
        for s in stale_sessions:
            s.status = "interrupted"
            s.error_message = "Analysis interrupted during server restart or worker failure."
        if count > 0:
            db.commit()
            logger.info("Recovered %d stale processing sessions -> INTERRUPTED", count)
        return count


session_service = SessionService()
