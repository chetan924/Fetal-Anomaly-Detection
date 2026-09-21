import uuid
from typing import Any, Dict, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.db.database import get_db
from app.inference.response_models import (
    ErrorCode,
    InferenceException,
    format_error_response,
    format_success_response,
)
from app.inference.upload_validator import (
    validate_image_upload,
    validate_vtk_upload,
)
from app.inference.worker_client import (
    worker_client,
)
from app.inference.worker_manager import (
    worker_manager,
)
from app.models.user import User
from app.services.comprehensive_analysis import (
    comprehensive_analysis_service,
)
from app.services.report_service import (
    report_service,
)
from app.services.session_service import (
    session_service,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/v1/inference",
    tags=["Multi-Model Inference"],
)


def _get_request_id(request: Optional[Request] = None) -> str:
    if request is not None and hasattr(request.state, "request_id") and request.state.request_id:
        return request.state.request_id
    return f"req_{uuid.uuid4().hex[:12]}"


def _clean_worker_payload(raw_result: Dict[str, Any]) -> Any:
    """
    Extracts the inner model data from worker response while preserving
    model-specific attributes.
    """
    if not isinstance(raw_result, dict):
        return raw_result

    # If worker returned {"status": "success", "result": {...}}
    if "result" in raw_result and len(raw_result) <= 4:
        return raw_result["result"]

    # Otherwise return the dictionary omitting redundant status/worker tags if desired,
    # or keep all keys intact.
    cleaned = dict(raw_result)
    cleaned.pop("status", None)
    return cleaned


# ============================================================
# 1. PLANE
# ============================================================

@router.get("/plane/health")
async def plane_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("plane")
    return format_success_response("plane", data, req_id)


@router.post("/plane")
async def plane_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="plane")
    raw_res = await worker_client.predict(
        model_name="plane",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("plane", data, req_id)


# ============================================================
# 2. SPINE
# ============================================================

@router.get("/spine/health")
async def spine_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("spine")
    return format_success_response("spine", data, req_id)


@router.post("/spine")
async def spine_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="spine")
    raw_res = await worker_client.predict(
        model_name="spine",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("spine", data, req_id)


# ============================================================
# 3. BRAIN
# ============================================================

@router.get("/brain/health")
async def brain_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("brain")
    return format_success_response("brain", data, req_id)


@router.post("/brain")
async def brain_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="brain")
    raw_res = await worker_client.predict(
        model_name="brain",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("brain", data, req_id)


# ============================================================
# 4. LUNG
# ============================================================

@router.get("/lung/health")
async def lung_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("lung")
    return format_success_response("lung", data, req_id)


@router.post("/lung")
async def lung_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="lung")
    raw_res = await worker_client.predict(
        model_name="lung",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("lung", data, req_id)


# ============================================================
# 5. BONE
# ============================================================

@router.get("/bone/health")
async def bone_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("bone")
    return format_success_response("bone", data, req_id)


@router.post("/bone")
async def bone_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="bone")
    raw_res = await worker_client.predict(
        model_name="bone",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("bone", data, req_id)


# ============================================================
# 6. PLACENTA
# ============================================================

@router.get("/placenta/health")
async def placenta_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("placenta")
    return format_success_response("placenta", data, req_id)


@router.post("/placenta")
async def placenta_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="placenta")
    raw_res = await worker_client.predict(
        model_name="placenta",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("placenta", data, req_id)


# ============================================================
# 7. FACE (3D VTK MESH)
# ============================================================

@router.get("/face/health")
async def face_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("face")
    return format_success_response("face", data, req_id)


@router.post("/face")
async def face_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_vtk_upload(file, model_name="face")
    raw_res = await worker_client.predict(
        model_name="face",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("face", data, req_id)


# ============================================================
# 8. HEART
# ============================================================

@router.get("/heart/health")
async def heart_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("heart")
    return format_success_response("heart", data, req_id)


@router.post("/heart")
async def heart_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    filename, content, content_type = await validate_image_upload(file, model_name="heart")
    raw_res = await worker_client.predict(
        model_name="heart",
        filename=filename,
        content=content,
        content_type=content_type,
        request_id=req_id,
    )
    data = _clean_worker_payload(raw_res)
    return format_success_response("heart", data, req_id)


# ============================================================
# 9. KIDNEY (DISABLED)
# ============================================================

@router.get("/kidney/health")
async def kidney_health(request: Request):
    req_id = _get_request_id(request)
    data = await worker_client.health("kidney")
    return format_success_response("kidney", data, req_id)


@router.post("/kidney")
async def kidney_inference(
    request: Request,
    file: UploadFile = File(...),
):
    req_id = _get_request_id(request)
    raise InferenceException(
        status_code=503,
        code=ErrorCode.WORKER_DISABLED,
        message="Kidney AI worker is currently disabled (model unavailable).",
        model="kidney",
    )


# ============================================================
# 10. COMPREHENSIVE FETAL ANALYSIS PIPELINE
# ============================================================

@router.post("/comprehensive")
async def comprehensive_inference(
    request: Request,
    plane_scan: Optional[UploadFile] = File(None),
    spine_scan: Optional[UploadFile] = File(None),
    brain_scan: Optional[UploadFile] = File(None),
    lung_scan: Optional[UploadFile] = File(None),
    bone_scan: Optional[UploadFile] = File(None),
    placenta_scan: Optional[UploadFile] = File(None),
    face_mesh: Optional[UploadFile] = File(None),
    heart_scan: Optional[UploadFile] = File(None),
    patient_id: Optional[str] = Form(None),
    idempotency_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Executes the multi-scan comprehensive fetal analysis pipeline with
    full analysis session lifecycle tracking and idempotency guarantees.
    """
    req_id = _get_request_id(request)
    user_id = current_user.id if current_user else None

    # 1. Idempotency & Session Setup
    session, was_created = session_service.create_or_get_session(
        db=db,
        patient_id=patient_id,
        created_by_user_id=user_id,
        idempotency_key=idempotency_key,
        session_id=session_id,
    )

    # If session already finished for this idempotency_key, return cached result
    if not was_created and session.status in ("completed", "partial", "failed") and session.result_json:
        cached_result = dict(session.result_json)
        existing_report = report_service.get_report(session.session_id, db)
        if existing_report:
            cached_result["report_number"] = existing_report.report_number
            cached_result["report_id"] = str(existing_report.id)
        cached_result["session_id"] = session.session_id
        cached_result["is_cached"] = True
        return format_success_response("comprehensive", cached_result, req_id)

    scan_slots = {
        "plane": plane_scan,
        "spine": spine_scan,
        "brain": brain_scan,
        "lung": lung_scan,
        "bone": bone_scan,
        "placenta": placenta_scan,
        "face": face_mesh,
        "heart": heart_scan,
    }

    requested_models = [
        k for k, v in scan_slots.items() if v is not None and getattr(v, "filename", None)
    ]

    # 2. Mark Session as Processing
    session_service.start_session_processing(
        session=session,
        requested_models=requested_models,
        db=db,
    )

    # 3. Execute Pipeline
    try:
        report = await comprehensive_analysis_service.run_pipeline(
            scan_slots=scan_slots,
            request_id=req_id,
            patient_id=patient_id,
            analysis_id=session.session_id,
        )
    except Exception as exc:
        session_service.complete_session(
            session=session,
            status="failed",
            summary={},
            result={},
            completed_models=[],
            failed_models=requested_models,
            db=db,
            error_message=str(exc),
        )
        raise

    # 4. Extract Completed & Failed Models
    findings = report.get("findings", {})
    completed_models = [k for k, v in findings.items() if v.get("status") == "completed"]
    failed_models = [k for k, v in findings.items() if v.get("status") == "failed"]

    # 5. Complete Session Record
    session_service.complete_session(
        session=session,
        status=report.get("status", "completed"),
        summary=report.get("summary", {}),
        result=report,
        completed_models=completed_models,
        failed_models=failed_models,
        db=db,
    )

    # 6. Persist Report Snapshot and Assign Sequential Report Number
    if report.get("status") != "no_inputs_provided":
        try:
            persisted = report_service.create_report_from_analysis(
                analysis_data=report,
                db=db,
                created_by_user_id=user_id,
                patient_id=patient_id,
            )
            report["report_number"] = persisted.report_number
            report["report_id"] = str(persisted.id)
        except Exception as exc:
            # Report persistence error should not break the return of inference findings
            pass

    report["session_id"] = session.session_id
    return format_success_response("comprehensive", report, req_id)


# ============================================================
# GENERIC MODEL HEALTH
# ============================================================

@router.get("/health/{model_name}")
async def model_health(
    model_name: str,
    request: Request,
):
    req_id = _get_request_id(request)
    try:
        data = await worker_client.health(model_name)
        return format_success_response(model_name, data, req_id)
    except ValueError as exc:
        raise InferenceException(
            status_code=404,
            code=ErrorCode.VALIDATION_ERROR,
            message=str(exc),
            model=model_name,
        ) from exc


# ============================================================
# WORKER LIFECYCLE STATUS
# ============================================================

@router.get("/workers/status")
async def workers_status(request: Request):
    """
    Returns the live state, PID, active requests, and idle
    metrics for all registered workers.
    """
    req_id = _get_request_id(request)
    status_dict = worker_manager.get_status()
    return format_success_response("registry", status_dict, req_id)


@router.get("/status")
async def status_alias(request: Request):
    """
    Alias for /workers/status.
    """
    return await workers_status(request)


@router.post("/workers/{model_name}/stop")
async def stop_worker_endpoint(
    model_name: str,
    request: Request,
):
    """
    Manually request stopping a specific worker process.
    """
    req_id = _get_request_id(request)
    try:
        stopped = await worker_manager.stop_worker(model_name, force=False)
        payload = {
            "worker": model_name,
            "stopped": stopped,
            "status": worker_manager.get_info(model_name).state.value,
        }
        return format_success_response(model_name, payload, req_id)
    except Exception as exc:
        raise InferenceException(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to stop worker '{model_name}': {exc}",
            model=model_name,
        ) from exc
