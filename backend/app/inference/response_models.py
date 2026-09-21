from typing import Any, Dict, Optional
from fastapi import HTTPException


# ============================================================
# STANDARD ERROR CODES
# ============================================================

class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_VTK = "INVALID_VTK"
    WORKER_DISABLED = "WORKER_DISABLED"
    WORKER_STARTUP_FAILED = "WORKER_STARTUP_FAILED"
    WORKER_UNAVAILABLE = "WORKER_UNAVAILABLE"
    WORKER_TIMEOUT = "WORKER_TIMEOUT"
    WORKER_CRASHED = "WORKER_CRASHED"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# ============================================================
# INFERENCE EXCEPTION
# ============================================================

class InferenceException(HTTPException):
    """
    Structured HTTP exception carrying a standardized error code,
    user-facing message, and optional model context.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        model: Optional[str] = None,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.model = model


# ============================================================
# RESPONSE BUILDERS
# ============================================================

def format_success_response(
    model: str,
    data: Any,
    request_id: str,
) -> Dict[str, Any]:
    """
    Wraps model inference results into the standardized success envelope.
    """
    return {
        "success": True,
        "model": model,
        "request_id": request_id,
        "data": data,
        "error": None,
    }


def format_error_response(
    model: Optional[str],
    code: str,
    message: str,
    request_id: str,
) -> Dict[str, Any]:
    """
    Formats an error response according to the standardized error envelope.
    """
    return {
        "success": False,
        "model": model,
        "request_id": request_id,
        "data": None,
        "error": {
            "code": code,
            "message": message,
        },
    }
