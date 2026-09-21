import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.core.audit_logger import security_audit
from app.db.database import get_db
from app.inference.response_models import ErrorCode, InferenceException, format_success_response
from app.models.user import User
from app.services.session_service import session_service
from app.services.report_service import report_service

router = APIRouter(
    prefix="/api/v1/analysis/sessions",
    tags=["Analysis Sessions"],
)


def _get_request_id(request: Optional[Request] = None) -> str:
    if request is not None and hasattr(request.state, "request_id") and request.state.request_id:
        return request.state.request_id
    return f"req_{uuid.uuid4().hex[:12]}"


def _serialize_session(s) -> Dict[str, Any]:
    return {
        "id": s.id,
        "session_id": s.session_id,
        "analysis_id": s.session_id,
        "patient_id": s.patient_id,
        "created_by": s.created_by,
        "status": s.status,
        "idempotency_key": s.idempotency_key,
        "requested_models": s.requested_models or [],
        "completed_models": s.completed_models or [],
        "failed_models": s.failed_models or [],
        "summary": s.summary_json or {},
        "result": s.result_json or {},
        "error_message": s.error_message,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


class CreateSessionPayload(BaseModel):
    patient_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    requested_models: Optional[List[str]] = None


# ============================================================
# 1. CREATE SESSION (DRAFT)
# ============================================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session_endpoint(
    payload: CreateSessionPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    
    session, was_created = session_service.create_or_get_session(
        db=db,
        patient_id=payload.patient_id,
        created_by_user_id=user_id,
        idempotency_key=payload.idempotency_key,
    )
    if payload.requested_models:
        session.requested_models = payload.requested_models
        db.commit()
        db.refresh(session)

    security_audit.log_resource_access(
        event_type="SESSION_CREATE",
        user_id=user_id,
        resource_type="analysis_session",
        resource_id=session.session_id,
        request=request,
        request_id=req_id,
        details={
            "patient_id": session.patient_id,
            "was_created": was_created,
            "idempotency_key": session.idempotency_key,
        },
    )

    resp_status = status.HTTP_201_CREATED if was_created else status.HTTP_200_OK
    return format_success_response("analysis_session", _serialize_session(session), req_id)


# ============================================================
# 2. LIST SESSIONS (PAGINATED & USER SCOPED)
# ============================================================
@router.get("")
async def list_sessions_endpoint(
    request: Request,
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None

    items, total = session_service.list_sessions(
        db=db,
        user_id=user_id,
        patient_id=patient_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    security_audit.log_resource_access(
        event_type="SESSION_LIST",
        user_id=user_id,
        resource_type="analysis_session",
        resource_id="list",
        request=request,
        request_id=req_id,
        details={"total": total, "page": page, "page_size": page_size},
    )
    data = {
        "items": [_serialize_session(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
    return format_success_response("analysis_session_list", data, req_id)


# ============================================================
# 3. GET SINGLE SESSION STATUS & RESULT
# ============================================================
@router.get("/{session_id}")
async def get_session_endpoint(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None

    session = session_service.get_session(session_id, db, user_id=user_id)
    if session is None:
        security_audit.log_authz_denied(
            user_id=user_id,
            resource_type="analysis_session",
            resource_id=session_id,
            action="VIEW",
            request=request,
            request_id=req_id,
        )
        raise InferenceException(
            status_code=404,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Analysis session '{session_id}' not found.",
            model="analysis_session",
        )
    security_audit.log_resource_access(
        event_type="SESSION_VIEW",
        user_id=user_id,
        resource_type="analysis_session",
        resource_id=session.session_id,
        request=request,
        request_id=req_id,
        details={"status": session.status},
    )
    return format_success_response("analysis_session", _serialize_session(session), req_id)


# ============================================================
# 4. RETRY / RECOVER SESSION
# ============================================================
@router.post("/{session_id}/retry")
async def retry_session_endpoint(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None

    session = session_service.get_session(session_id, db, user_id=user_id)
    if session is None:
        security_audit.log_authz_denied(
            user_id=user_id,
            resource_type="analysis_session",
            resource_id=session_id,
            action="RETRY",
            request=request,
            request_id=req_id,
        )
        raise InferenceException(
            status_code=404,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Analysis session '{session_id}' not found.",
            model="analysis_session",
        )

    if session.status not in ("interrupted", "failed", "partial"):
        return format_success_response(
            "analysis_session",
            {
                "session": _serialize_session(session),
                "message": f"Session status is '{session.status}'; retry not needed.",
            },
            req_id,
        )

    session.status = "ready"
    session.error_message = None
    db.commit()
    db.refresh(session)
    security_audit.log_resource_access(
        event_type="SESSION_RETRY",
        user_id=user_id,
        resource_type="analysis_session",
        resource_id=session.session_id,
        request=request,
        request_id=req_id,
        details={"status": "ready"},
    )
    return format_success_response("analysis_session", _serialize_session(session), req_id)
