import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import Request

# Dedicated Security Audit Logger
audit_logger = logging.getLogger("fetalai.security_audit")

# Sensitive keys that must NEVER be recorded in audit logs
SENSITIVE_KEYS = {
    "password",
    "current_password",
    "new_password",
    "hashed_password",
    "token",
    "access_token",
    "reset_token",
    "reset_token_hash",
    "otp",
    "otp_hash",
    "secret",
    "jwt_secret_key",
    "authorization",
}


def sanitize_audit_data(data: Any) -> Any:
    """
    Recursively redacts passwords, tokens, OTPs, and binary payloads
    from audit log metadata dictionaries.
    """
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_KEYS:
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, (bytes, bytearray)):
                cleaned[k] = f"<{len(v)} bytes binary payload>"
            elif isinstance(v, (dict, list)):
                cleaned[k] = sanitize_audit_data(v)
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [sanitize_audit_data(item) for item in data]
    return data


def extract_client_ip(request: Optional[Request]) -> Optional[str]:
    """
    Safely resolves client IP from X-Forwarded-For or socket address.
    """
    if request is None:
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


class AuditLogger:
    """
    Centralized Security Audit Trail Engine.
    Emits structured, machine-parsable security event records.
    """

    @staticmethod
    def log_event(
        event_type: str,
        status: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        now_utc = datetime.now(timezone.utc).isoformat()
        cleaned_details = sanitize_audit_data(details or {})

        record = {
            "timestamp": now_utc,
            "event_type": event_type,
            "status": status.upper(),
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id is not None else None,
            "request_id": request_id,
            "client_ip": client_ip,
            "details": cleaned_details,
        }

        message = json.dumps(record, default=str)
        if status.upper() in ("FAILURE", "DENIED", "BLOCKED"):
            audit_logger.warning("SECURITY_AUDIT: %s", message)
        else:
            audit_logger.info("SECURITY_AUDIT: %s", message)

        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_security_event(event_type, status)
        except Exception:
            pass

    @classmethod
    def log_auth_success(
        cls,
        user_id: int,
        email: str,
        event_type: str = "AUTH_LOGIN_SUCCESS",
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
    ) -> None:
        client_ip = extract_client_ip(request)
        cls.log_event(
            event_type=event_type,
            status="SUCCESS",
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            request_id=request_id,
            client_ip=client_ip,
            details={"email": email},
        )

    @classmethod
    def log_auth_failure(
        cls,
        email: str,
        reason: str,
        event_type: str = "AUTH_LOGIN_FAILURE",
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
    ) -> None:
        client_ip = extract_client_ip(request)
        cls.log_event(
            event_type=event_type,
            status="FAILURE",
            user_id=None,
            resource_type="user",
            resource_id=email,
            request_id=request_id,
            client_ip=client_ip,
            details={"email": email, "reason": reason},
        )

    @classmethod
    def log_authz_denied(
        cls,
        user_id: Optional[int],
        resource_type: str,
        resource_id: str,
        action: str,
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
    ) -> None:
        client_ip = extract_client_ip(request)
        cls.log_event(
            event_type="AUTHZ_DENIED",
            status="DENIED",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            client_ip=client_ip,
            details={"action": action, "reason": "Ownership mismatch or unauthorized access attempt"},
        )

    @classmethod
    def log_resource_access(
        cls,
        event_type: str,
        user_id: Optional[int],
        resource_type: str,
        resource_id: str,
        status: str = "SUCCESS",
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        client_ip = extract_client_ip(request)
        cls.log_event(
            event_type=event_type,
            status=status,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            client_ip=client_ip,
            details=details,
        )


security_audit = AuditLogger()
