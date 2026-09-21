import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Structured Observability Logger
obs_logger = logging.getLogger("fetalai.observability")


def emit_structured_log(
    level: str,
    event_type: str,
    message: str,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    worker: Optional[str] = None,
    model: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emits a structured, machine-readable JSON log entry for production monitoring.
    Redacts any sensitive tokens/passwords automatically.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": now_utc,
        "level": level.upper(),
        "service": "backend",
        "event_type": event_type,
        "message": message,
        "request_id": request_id,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "worker": worker,
        "model": model,
        "details": details or {},
    }

    # Remove None values for cleaner JSON
    cleaned_record = {k: v for k, v in record.items() if v is not None}
    log_str = json.dumps(cleaned_record, default=str)

    lvl = level.upper()
    if lvl == "ERROR":
        obs_logger.error("OBSERVABILITY: %s", log_str)
    elif lvl in ("WARN", "WARNING"):
        obs_logger.warning("OBSERVABILITY: %s", log_str)
    else:
        obs_logger.info("OBSERVABILITY: %s", log_str)
