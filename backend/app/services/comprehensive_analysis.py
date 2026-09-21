import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import UploadFile

from app.inference.response_models import ErrorCode, InferenceException
from app.inference.upload_validator import validate_image_upload, validate_vtk_upload
from app.inference.worker_client import worker_client
from app.inference.model_registry import MODEL_WORKERS

logger = logging.getLogger("fetalai.comprehensive_pipeline")

# ============================================================
# COMPREHENSIVE PIPELINE SERVICE
# ============================================================

ALL_ANATOMICAL_MODELS = [
    "plane",
    "spine",
    "brain",
    "lung",
    "bone",
    "placenta",
    "face",
    "heart",
    "kidney",
]

MEDICAL_DISCLAIMER_TEXT = (
    "AI model outputs are experimental clinical decision-support and research "
    "outputs. They do not constitute a medical diagnosis or confirmed clinical finding."
)


def _clean_worker_result(raw_result: Dict[str, Any]) -> Any:
    """
    Extracts the inner model data from worker response while preserving
    model-specific attributes.
    """
    if not isinstance(raw_result, dict):
        return raw_result
    if "result" in raw_result and len(raw_result) <= 4:
        return raw_result["result"]
    cleaned = dict(raw_result)
    cleaned.pop("status", None)
    return cleaned


class ComprehensiveAnalysisService:
    """
    Orchestrates multi-scan comprehensive fetal analysis across
    isolated worker processes.
    
    Guarantees:
    - Zero ML frameworks loaded in Gateway process
    - Memory-safe sequential worker execution
    - Failure tolerance: partial successes are preserved
    - Model-specific output preservation
    - Standard status semantics for all anatomical targets
    """

    async def run_pipeline(
        self,
        scan_slots: Dict[str, Optional[UploadFile]],
        request_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        t_start = time.time()
        analysis_id = analysis_id or f"an_{uuid.uuid4().hex[:12]}"
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"

        logger.info(
            "Starting comprehensive analysis: analysis_id=%s request_id=%s patient_id=%s",
            analysis_id,
            req_id,
            patient_id,
        )

        findings: Dict[str, Dict[str, Any]] = {}
        warnings: List[str] = []
        errors: List[Dict[str, Any]] = []

        models_requested = 0
        models_completed = 0
        models_failed = 0
        models_not_provided = 0
        models_unavailable = 0

        # 1. Inspect inputs & schedule models
        valid_tasks: List[Dict[str, Any]] = []

        for model_name in ALL_ANATOMICAL_MODELS:
            # Check if model is disabled in registry (e.g. Kidney)
            cfg = MODEL_WORKERS.get(model_name, {})
            if cfg.get("disabled", False):
                models_unavailable += 1
                findings[model_name] = {
                    "status": "unavailable",
                    "reason": cfg.get("disabled_reason", "model unavailable"),
                    "model": model_name,
                }
                continue

            upload_file = scan_slots.get(model_name)

            if upload_file is None or not upload_file.filename:
                models_not_provided += 1
                findings[model_name] = {
                    "status": "not_provided",
                    "model": model_name,
                }
                continue

            models_requested += 1

            # 2. Validate input format before worker dispatch
            try:
                if model_name == "face":
                    filename, file_bytes, content_type = await validate_vtk_upload(
                        upload_file, model_name="face"
                    )
                else:
                    filename, file_bytes, content_type = await validate_image_upload(
                        upload_file, model_name=model_name
                    )

                valid_tasks.append({
                    "model_name": model_name,
                    "filename": filename,
                    "content": file_bytes,
                    "content_type": content_type,
                })

            except InferenceException as exc:
                models_failed += 1
                err_detail = {
                    "code": exc.code.value if hasattr(exc.code, "value") else str(exc.code),
                    "message": exc.message,
                }
                findings[model_name] = {
                    "status": "failed",
                    "model": model_name,
                    "error": err_detail,
                }
                errors.append({
                    "model": model_name,
                    "error": err_detail,
                })
            except Exception as exc:
                models_failed += 1
                err_detail = {
                    "code": ErrorCode.VALIDATION_ERROR.value,
                    "message": f"Validation failed: {exc}",
                }
                findings[model_name] = {
                    "status": "failed",
                    "model": model_name,
                    "error": err_detail,
                }
                errors.append({
                    "model": model_name,
                    "error": err_detail,
                })

        # 3. Controlled Sequential Execution (Memory Safe for ~512 MB Environment)
        for task in valid_tasks:
            model_name = task["model_name"]
            t0 = time.time()
            try:
                raw_res = await worker_client.predict(
                    model_name=model_name,
                    filename=task["filename"],
                    content=task["content"],
                    content_type=task["content_type"],
                    request_id=req_id,
                )
                duration_ms = round((time.time() - t0) * 1000, 2)
                cleaned_data = _clean_worker_result(raw_res)

                models_completed += 1
                findings[model_name] = {
                    "status": "completed",
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "result": cleaned_data,
                }
                logger.info(
                    "Model inference succeeded: analysis_id=%s model=%s duration_ms=%s",
                    analysis_id,
                    model_name,
                    duration_ms,
                )

            except InferenceException as exc:
                models_failed += 1
                duration_ms = round((time.time() - t0) * 1000, 2)
                err_detail = {
                    "code": exc.code.value if hasattr(exc.code, "value") else str(exc.code),
                    "message": exc.message,
                }
                findings[model_name] = {
                    "status": "failed",
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "error": err_detail,
                }
                errors.append({
                    "model": model_name,
                    "error": err_detail,
                })
                logger.warning(
                    "Model inference failed: analysis_id=%s model=%s error=%s",
                    analysis_id,
                    model_name,
                    exc.message,
                )

            except Exception as exc:
                models_failed += 1
                duration_ms = round((time.time() - t0) * 1000, 2)
                err_detail = {
                    "code": ErrorCode.INFERENCE_FAILED.value,
                    "message": f"Inference execution failed: {exc}",
                }
                findings[model_name] = {
                    "status": "failed",
                    "model": model_name,
                    "duration_ms": duration_ms,
                    "error": err_detail,
                }
                errors.append({
                    "model": model_name,
                    "error": err_detail,
                })
                logger.error(
                    "Model unexpected error: analysis_id=%s model=%s error=%s",
                    analysis_id,
                    model_name,
                    exc,
                )

        # 4. Determine overall analysis status
        if models_requested == 0:
            overall_status = "no_inputs_provided"
            warnings.append("No valid scan files were provided for analysis.")
        elif models_completed == models_requested:
            overall_status = "completed"
        elif models_completed > 0:
            overall_status = "partial"
            warnings.append(
                f"{models_completed} of {models_requested} requested model analyses completed successfully."
            )
        else:
            overall_status = "failed"
            warnings.append("All requested model analyses failed.")

        total_duration = round(time.time() - t_start, 2)
        total_duration_ms = round((time.time() - t_start) * 1000, 2)

        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            metrics_collector.record_comprehensive_analysis(
                duration_ms=total_duration_ms,
                status=overall_status,
                requested_count=models_requested,
                completed_count=models_completed,
                failed_count=models_failed,
                unavailable_count=models_unavailable,
            )
            emit_structured_log(
                "INFO",
                "COMPREHENSIVE_ANALYSIS",
                f"Comprehensive analysis {analysis_id} finished ({overall_status}) in {total_duration_ms:.2f}ms",
                request_id=req_id,
                duration_ms=total_duration_ms,
                details={
                    "analysis_id": analysis_id,
                    "status": overall_status,
                    "models_requested": models_requested,
                    "models_completed": models_completed,
                    "models_failed": models_failed,
                },
            )
        except Exception:
            pass

        return {
            "analysis_id": analysis_id,
            "request_id": req_id,
            "patient_id": patient_id,
            "status": overall_status,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "summary": {
                "overall_status": overall_status,
                "models_requested": models_requested,
                "models_completed": models_completed,
                "models_failed": models_failed,
                "models_not_provided": models_not_provided,
                "models_unavailable": models_unavailable,
                "total_duration_seconds": total_duration,
            },
            "findings": findings,
            "warnings": warnings,
            "errors": errors,
            "disclaimer": {
                "text": MEDICAL_DISCLAIMER_TEXT,
                "is_medical_diagnosis": False,
            },
        }


comprehensive_analysis_service = ComprehensiveAnalysisService()
