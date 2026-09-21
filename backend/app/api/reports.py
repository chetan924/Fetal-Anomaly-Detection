import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.core.audit_logger import security_audit
from app.db.database import get_db
from app.inference.response_models import ErrorCode, InferenceException, format_error_response, format_success_response
from app.models.user import User
from app.services.report_service import report_service

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Clinical Reports"],
)


def _get_request_id(request: Optional[Request] = None) -> str:
    if request is not None and hasattr(request.state, "request_id") and request.state.request_id:
        return request.state.request_id
    return f"req_{uuid.uuid4().hex[:12]}"


def _serialize_report(report) -> Dict[str, Any]:
    return {
        "id": report.id,
        "report_id": str(report.id),
        "report_number": report.report_number,
        "analysis_id": report.analysis_id,
        "patient_id": report.patient_id,
        "created_by": report.created_by,
        "status": report.status,
        "result": report.result_json,
        "summary": report.summary_json,
        "warnings": report.warnings_json or [],
        "errors": report.errors_json or [],
        "is_archived": report.is_archived,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }


class CreateReportPayload(BaseModel):
    analysis_result: Dict[str, Any]
    patient_id: Optional[str] = None


# ============================================================
# 1. CREATE REPORT SNAPSHOT
# ============================================================
@router.post("", status_code=status.HTTP_201_CREATED)
async def create_report_endpoint(
    payload: CreateReportPayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    try:
        report = report_service.create_report_from_analysis(
            analysis_data=payload.analysis_result,
            db=db,
            created_by_user_id=user_id,
            patient_id=payload.patient_id,
        )
        security_audit.log_resource_access(
            event_type="REPORT_CREATE",
            user_id=user_id,
            resource_type="report",
            resource_id=str(report.id),
            request=request,
            request_id=req_id,
            details={
                "report_number": report.report_number,
                "analysis_id": report.analysis_id,
                "patient_id": report.patient_id,
            },
        )
        return format_success_response("report", _serialize_report(report), req_id)
    except Exception as exc:
        raise InferenceException(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to create report snapshot: {exc}",
            model="report",
        ) from exc


# ============================================================
# 2. LIST REPORTS (PAGINATED & SEARCHABLE)
# ============================================================
@router.get("")
async def list_reports_endpoint(
    request: Request,
    patient_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    items, total = report_service.list_reports(
        db=db,
        user_id=user_id,
        patient_id=patient_id,
        status=status,
        search=search,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    security_audit.log_resource_access(
        event_type="REPORT_LIST",
        user_id=user_id,
        resource_type="report",
        resource_id="list",
        request=request,
        request_id=req_id,
        details={"total": total, "page": page, "page_size": page_size},
    )
    data = {
        "items": [_serialize_report(r) for r in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
    return format_success_response("report_list", data, req_id)


# ============================================================
# 3. GET SINGLE REPORT DETAILS
# ============================================================
@router.get("/{identifier}")
async def get_report_endpoint(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    report = report_service.get_report(identifier, db, user_id=user_id)
    if report is None:
        security_audit.log_authz_denied(
            user_id=user_id,
            resource_type="report",
            resource_id=identifier,
            action="VIEW",
            request=request,
            request_id=req_id,
        )
        raise InferenceException(
            status_code=404,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Report '{identifier}' was not found.",
            model="report",
        )
    security_audit.log_resource_access(
        event_type="REPORT_VIEW",
        user_id=user_id,
        resource_type="report",
        resource_id=str(report.id),
        request=request,
        request_id=req_id,
        details={"report_number": report.report_number},
    )
    return format_success_response("report", _serialize_report(report), req_id)


# ============================================================
# 4. DOWNLOAD REPORT PDF
# ============================================================
@router.get("/{identifier}/pdf")
async def download_report_pdf(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    report = report_service.get_report(identifier, db, user_id=user_id)
    if report is None:
        security_audit.log_authz_denied(
            user_id=user_id,
            resource_type="report",
            resource_id=identifier,
            action="DOWNLOAD_PDF",
            request=request,
            request_id=req_id,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Report '{identifier}' not found.",
        )

    try:
        pdf_bytes = report_service.generate_pdf_bytes(report)
        filename = f"{report.report_number}.pdf"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        }
        security_audit.log_resource_access(
            event_type="REPORT_PDF_DOWNLOAD",
            user_id=user_id,
            resource_type="report",
            resource_id=str(report.id),
            request=request,
            request_id=req_id,
            details={"report_number": report.report_number, "bytes": len(pdf_bytes)},
        )
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF for report {report.report_number}: {exc}",
        ) from exc


# ============================================================
# 5. ARCHIVE REPORT
# ============================================================
@router.post("/{identifier}/archive")
async def archive_report_endpoint(
    identifier: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None
    report = report_service.get_report(identifier, db, user_id=user_id)
    if report is None:
        security_audit.log_authz_denied(
            user_id=user_id,
            resource_type="report",
            resource_id=identifier,
            action="ARCHIVE",
            request=request,
            request_id=req_id,
        )
        raise InferenceException(
            status_code=404,
            code=ErrorCode.VALIDATION_ERROR,
            message=f"Report '{identifier}' not found.",
            model="report",
        )
    success = report_service.archive_report(identifier, db, user_id=user_id)
    security_audit.log_resource_access(
        event_type="REPORT_ARCHIVE",
        user_id=user_id,
        resource_type="report",
        resource_id=str(report.id),
        request=request,
        request_id=req_id,
        details={"report_number": report.report_number},
    )
    return format_success_response("report", {"report_number": report.report_number, "is_archived": True, "archived": True}, req_id)
