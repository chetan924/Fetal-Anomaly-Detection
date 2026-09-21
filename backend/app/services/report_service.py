import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.report import Report
from app.services.pdf_generator import generate_fetal_report_pdf

logger = logging.getLogger("fetalai.report_service")
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class ReportService:
    """
    Manages clinical report snapshots, sequential concurrency-safe
    report numbering (FETAL-RPT-000001), query filtering, and PDF generation.
    """

    def create_report_from_analysis(
        self,
        analysis_data: Dict[str, Any],
        db: Session,
        created_by_user_id: Optional[int] = None,
        patient_id: Optional[str] = None,
    ) -> Report:
        """
        Creates and persists an immutable report snapshot from a comprehensive
        fetal analysis result dictionary.
        """
        analysis_id = analysis_data.get("analysis_id") or f"an_{uuid.uuid4().hex[:12]}"
        status = analysis_data.get("status", "completed")
        summary_data = analysis_data.get("summary", {})
        warnings = analysis_data.get("warnings", [])
        errors = analysis_data.get("errors", [])
        resolved_patient_id = patient_id or analysis_data.get("patient_id")

        # 1. Check if report already exists for this analysis_id to avoid duplicate creation
        existing = db.scalar(
            select(Report).where(Report.analysis_id == analysis_id)
        )
        if existing is not None:
            logger.info("Report already exists for analysis_id=%s (report_number=%s)", analysis_id, existing.report_number)
            return existing

        # 2. Concurrency-Safe Sequential Report Number Generation
        temp_token = f"TEMP-{uuid.uuid4().hex}"
        report = Report(
            report_number=temp_token,
            analysis_id=analysis_id,
            patient_id=resolved_patient_id,
            created_by=created_by_user_id,
            status=status,
            result_json=analysis_data,
            summary_json=summary_data,
            warnings_json=warnings,
            errors_json=errors,
            is_archived=False,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(report)
        db.flush()

        # Format stable human-friendly sequential report number: FETAL-RPT-000001
        report.report_number = f"FETAL-RPT-{report.id:06d}"
        db.commit()
        db.refresh(report)

        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            metrics_collector.record_report_generation(duration_ms=0.0, success=True)
            emit_structured_log(
                "INFO",
                "REPORT_GENERATED",
                f"Report {report.report_number} generated for analysis {report.analysis_id}",
                details={
                    "report_id": report.id,
                    "report_number": report.report_number,
                    "analysis_id": report.analysis_id,
                    "status": report.status,
                },
            )
        except Exception:
            pass

        logger.info(
            "Created Report: report_id=%s report_number=%s analysis_id=%s status=%s created_by=%s",
            report.id,
            report.report_number,
            report.analysis_id,
            report.status,
            report.created_by,
        )
        return report

    def get_report(
        self,
        identifier: str | int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> Optional[Report]:
        """
        Fetches report by numeric ID, report_number (FETAL-RPT-000001), or analysis_id.
        Enforces strict authorization:
        - Authenticated user: can access own reports and unassigned/prototype reports.
        - Anonymous user: can ONLY access unassigned/prototype reports (created_by is None).
        """
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            num_id = int(identifier)
            stmt = select(Report).where(Report.id == num_id)
        else:
            ident_str = str(identifier).strip()
            stmt = select(Report).where(
                or_(
                    Report.report_number == ident_str,
                    Report.analysis_id == ident_str,
                )
            )

        if user_id is not None:
            stmt = stmt.where(
                or_(
                    Report.created_by == user_id,
                    Report.created_by.is_(None),
                )
            )
        else:
            stmt = stmt.where(Report.created_by.is_(None))

        return db.scalar(stmt)

    def list_reports(
        self,
        db: Session,
        user_id: Optional[int] = None,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Report], int]:
        """
        Returns a paginated list of reports with total count, scoped to user.
        """
        stmt = select(Report)

        if not include_archived:
            stmt = stmt.where(Report.is_archived.is_(False))

        if user_id is not None:
            stmt = stmt.where(
                or_(
                    Report.created_by == user_id,
                    Report.created_by.is_(None),
                )
            )
        else:
            stmt = stmt.where(Report.created_by.is_(None))

        if patient_id:
            stmt = stmt.where(Report.patient_id == patient_id.strip())

        if status:
            stmt = stmt.where(Report.status == status.strip().lower())

        if search:
            s = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Report.report_number.ilike(s),
                    Report.analysis_id.ilike(s),
                    Report.patient_id.ilike(s),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        # Sort newest first
        stmt = stmt.order_by(Report.created_at.desc())

        # Pagination
        offset = max(0, (page - 1) * page_size)
        stmt = stmt.offset(offset).limit(page_size)

        items = list(db.scalars(stmt).all())
        return items, total

    def archive_report(
        self,
        identifier: str | int,
        db: Session,
        user_id: Optional[int] = None,
    ) -> bool:
        report = self.get_report(identifier, db, user_id=user_id)
        if report is None:
            return False
        report.is_archived = True
        report.status = "archived"
        db.commit()
        return True

    def generate_pdf_bytes(
        self,
        report: Report,
    ) -> bytes:
        """
        Renders the PDF report binary for the given report snapshot.
        """
        import time
        t_start = time.time()
        report_data = {
            "id": report.id,
            "report_number": report.report_number,
            "analysis_id": report.analysis_id,
            "patient_id": report.patient_id,
            "status": report.status,
            "created_at": report.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if report.created_at else "",
            "result_json": report.result_json,
            "summary_json": report.summary_json,
            "warnings_json": report.warnings_json,
            "errors_json": report.errors_json,
        }
        try:
            pdf_data = generate_fetal_report_pdf(report_data, backend_root=BACKEND_ROOT)
            dur_ms = round((time.time() - t_start) * 1000, 2)
            try:
                from app.core.metrics import metrics_collector
                from app.core.observability_logger import emit_structured_log
                metrics_collector.record_pdf_generation(dur_ms, success=True)
                emit_structured_log(
                    "INFO",
                    "PDF_GENERATION",
                    f"PDF generated for {report.report_number} in {dur_ms:.2f}ms",
                    duration_ms=dur_ms,
                    details={"report_number": report.report_number, "bytes": len(pdf_data)},
                )
            except Exception:
                pass
            return pdf_data
        except Exception as exc:
            dur_ms = round((time.time() - t_start) * 1000, 2)
            try:
                from app.core.metrics import metrics_collector
                from app.core.observability_logger import emit_structured_log
                metrics_collector.record_pdf_generation(dur_ms, success=False)
                emit_structured_log(
                    "ERROR",
                    "PDF_GENERATION_FAILED",
                    f"PDF generation failed for {report.report_number}: {exc}",
                    duration_ms=dur_ms,
                    details={"report_number": report.report_number, "error": str(exc)},
                )
            except Exception:
                pass
            raise


report_service = ReportService()
