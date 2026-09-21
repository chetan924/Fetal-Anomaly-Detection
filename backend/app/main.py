import logging
import time
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Setup logger
logger = logging.getLogger("fetalai.api")


# =========================================================
# API ROUTERS
# =========================================================

from app.api.auth import router as auth_router
from app.api.patients import router as patients_router
from app.api.ai import router as ai_router
from app.api.scans import router as scans_router
from app.api.reports import router as reports_router
from app.api.analysis_sessions import router as analysis_sessions_router
from app.services.session_service import session_service
from app.db.database import SessionLocal, Base, engine, check_database_connection


# =========================================================
# MULTI-MODEL INFERENCE ROUTER & LIFECYCLE
# =========================================================

from app.inference.router import router as inference_router
from app.inference.worker_manager import worker_manager
from app.inference.response_models import (
    ErrorCode,
    InferenceException,
    format_error_response,
)


# =========================================================
# CORE CONFIG, RATE LIMITING & RELIABILITY
# =========================================================

from app.core.config import (
    ADDITIONAL_FRONTEND_ORIGINS,
    ENVIRONMENT,
    FRONTEND_URL,
    SECURITY_HEADERS_ENABLED,
    HSTS_ENABLED,
)
from app.core.rate_limiter import rate_limiter
from app.core.alert_manager import alert_manager, AlertSeverity, ServiceHealthStatus


# =========================================================
# MODELS
# =========================================================

from app.models.user import User
from app.models.patient import Patient
from app.models.scan import Scan
from app.models.report import Report


# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="FetalAI API",
    version="0.1.0",
    description="AI-assisted fetal anomaly screening prototype API Gateway",
)


# =========================================================
# PATH CONFIGURATION
# =========================================================

APP_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = APP_DIR.parent
STORAGE_DIR = BACKEND_ROOT / "storage"
SCAN_STORAGE_DIR = STORAGE_DIR / "scans"
EXPLAINABILITY_STORAGE_DIR = STORAGE_DIR / "explainability"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)
SCAN_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
EXPLAINABILITY_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# STATIC STORAGE
# =========================================================

app.mount(
    "/storage",
    StaticFiles(directory=str(STORAGE_DIR), check_dir=True),
    name="storage",
)


# =========================================================
# DATABASE INIT
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# SECURITY HEADERS MIDDLEWARE
# =========================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' https: data:; "
                "style-src 'self' 'unsafe-inline' https:; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            )
            # Enforce HSTS if configured or in production with HTTPS
            is_https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
            if HSTS_ENABLED or (ENVIRONMENT == "production" and is_https):
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response


# =========================================================
# RATE LIMITING MIDDLEWARE
# =========================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        # Extract client IP (handle proxy / forwarded headers safely)
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        category = rate_limiter.get_category_for_path(request.url.path)
        allowed, retry_after = rate_limiter.is_allowed(client_ip, category)

        if not allowed:
            req_id = getattr(request.state, "request_id", None) or f"req_{uuid4().hex[:12]}"
            if request.url.path.startswith("/api/v1/inference"):
                return JSONResponse(
                    status_code=429,
                    content=format_error_response(
                        model=None,
                        code=ErrorCode.RATE_LIMIT_EXCEEDED,
                        message="Rate limit exceeded. Please try again later.",
                        request_id=req_id,
                    ),
                    headers={"Retry-After": str(retry_after), "X-Request-ID": req_id},
                )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later.", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after), "X-Request-ID": req_id},
            )

        return await call_next(request)


# =========================================================
# CORS CONFIGURATION
# =========================================================

allowed_origins = {
    "https://fetal-anomaly-detection.onrender.com",
    "https://fetalai-backend.onrender.com",
}

if FRONTEND_URL:
    fe_origin = FRONTEND_URL.strip().rstrip("/")
    if fe_origin:
        allowed_origins.add(fe_origin)

for extra in ADDITIONAL_FRONTEND_ORIGINS:
    if extra:
        allowed_origins.add(extra)

if ENVIRONMENT != "production":
    allowed_origins.update({
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    })

allowed_origins = list(allowed_origins)

# Add Middlewares (executed in reverse order: Request ID -> Security Headers -> Rate Limit -> CORS)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)


# =========================================================
# REQUEST ID & LOGGING MIDDLEWARE
# =========================================================

@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    raw_req_id = request.headers.get("X-Request-ID")
    req_id = raw_req_id.strip() if raw_req_id and raw_req_id.strip() else f"req_{uuid4().hex[:12]}"
    request.state.request_id = req_id
    start_time = time.time()

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id

        # Record metrics and emit structured log
        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            is_slow = metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=req_id,
            )
            if is_slow:
                emit_structured_log(
                    "WARN",
                    "SLOW_REQUEST",
                    f"Request exceeded threshold ({duration_ms:.2f}ms >= {metrics_collector.slow_threshold_ms}ms)",
                    request_id=req_id,
                    endpoint=f"{request.method} {request.url.path}",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
            elif request.url.path.startswith("/api/v1/inference"):
                emit_structured_log(
                    "INFO",
                    "HTTP_REQUEST",
                    f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)",
                    request_id=req_id,
                    endpoint=f"{request.method} {request.url.path}",
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                )
        except Exception:
            pass

        return response

    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        try:
            from app.core.metrics import metrics_collector
            from app.core.observability_logger import emit_structured_log
            metrics_collector.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                request_id=req_id,
            )
            emit_structured_log(
                "ERROR",
                "HTTP_EXCEPTION",
                f"Unhandled exception on {request.method} {request.url.path}: {exc}",
                request_id=req_id,
                endpoint=f"{request.method} {request.url.path}",
                status_code=500,
                duration_ms=duration_ms,
                details={"error": str(exc)},
            )
        except Exception:
            pass
        logger.error(
            "request_id=%s method=%s path=%s error=%s duration_ms=%.2f",
            req_id,
            request.method,
            request.url.path,
            exc,
            duration_ms,
        )
        raise


# =========================================================
# EXCEPTION HANDLERS
# =========================================================

@app.exception_handler(InferenceException)
async def inference_exception_handler(request: Request, exc: InferenceException):
    req_id = getattr(request.state, "request_id", None) or f"req_{uuid4().hex[:12]}"
    return JSONResponse(
        status_code=exc.status_code,
        content=format_error_response(
            model=exc.model,
            code=exc.code,
            message=exc.message,
            request_id=req_id,
        ),
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # If the error is on an inference route, wrap in standard envelope
    if request.url.path.startswith("/api/v1/inference"):
        req_id = getattr(request.state, "request_id", None) or f"req_{uuid4().hex[:12]}"
        code = ErrorCode.VALIDATION_ERROR if exc.status_code in (400, 422) else ErrorCode.INTERNAL_ERROR
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(
                model=None,
                code=code,
                message=str(exc.detail),
                request_id=req_id,
            ),
            headers={"X-Request-ID": req_id},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None) or f"req_{uuid4().hex[:12]}"
    logger.exception("Unhandled error on %s (request_id=%s): %s", request.url.path, req_id, exc)
    if request.url.path.startswith("/api/v1/inference"):
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                model=None,
                code=ErrorCode.INTERNAL_ERROR,
                message="An internal server error occurred while processing the request.",
                request_id=req_id,
            ),
            headers={"X-Request-ID": req_id},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(ai_router)
app.include_router(scans_router)
app.include_router(reports_router)
app.include_router(analysis_sessions_router)
app.include_router(inference_router)


# =========================================================
# WORKER LIFECYCLE HOOKS
# =========================================================

@app.on_event("startup")
async def startup_event():
    """
    Start the background idle worker reaper task on Gateway startup
    and recover any stale interrupted sessions.
    """
    worker_manager.start_reaper_task()
    try:
        db = SessionLocal()
        try:
            session_service.recover_stale_sessions(db)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Failed to recover stale sessions on startup: %s", exc)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Gracefully terminate all managed child worker processes on Gateway shutdown.
    """
    await worker_manager.stop_all_workers()


# =========================================================
# HEALTH, RELIABILITY & PROBE ENDPOINTS
# =========================================================

@app.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Liveness probe: verifies Gateway process vitality, memory posture, and unified health status.
    """
    from app.core.metrics import metrics_collector
    mem = metrics_collector.get_memory_metrics()
    firing = alert_manager.get_alerts(active_only=True)
    crit_count = sum(1 for a in firing if a.get("severity") == "CRITICAL")
    warn_count = sum(1 for a in firing if a.get("severity") == "WARNING")

    if crit_count > 0:
        health_status = ServiceHealthStatus.UNAVAILABLE.value
    elif warn_count > 0 or mem.get("is_high_memory_pressure", False):
        health_status = ServiceHealthStatus.DEGRADED.value
    else:
        health_status = ServiceHealthStatus.HEALTHY.value

    return {
        "status": "ok",
        "health_status": health_status,
        "service": "backend",
        "environment": ENVIRONMENT,
        "uptime_seconds": mem["uptime_seconds"],
        "memory_mb": mem["rss_mb"],
        "high_memory_warning": mem["is_high_memory_pressure"],
        "active_alerts_count": len(firing),
    }


@app.get("/health/readiness")
def readiness_check():
    """
    Readiness probe: verifies database connectivity, latency, and comprehensive system health.
    """
    ok, err = check_database_connection()
    from app.core.metrics import metrics_collector
    mem = metrics_collector.get_memory_metrics()
    worker_statuses = worker_manager.get_status()

    health_eval = alert_manager.evaluate_system_health(
        metrics_summary=metrics_collector.get_summary(),
        db_healthy=ok,
        db_latency_ms=metrics_collector.last_db_ping_latency_ms,
        worker_statuses=worker_statuses,
    )

    if ok:
        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "health_status": health_eval["overall_status"],
                "database": "connected",
                "database_latency_ms": metrics_collector.last_db_ping_latency_ms,
                "workers": "available",
                "memory": {
                    "rss_mb": mem["rss_mb"],
                    "high_memory_pressure": mem["is_high_memory_pressure"],
                },
                "active_alerts_count": health_eval["summary"]["total_firing"],
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "status": "unhealthy",
            "health_status": ServiceHealthStatus.UNAVAILABLE.value,
            "database": "disconnected",
            "error": "Database connectivity check failed",
            "workers": "available",
            "active_alerts_count": health_eval["summary"]["total_firing"],
        },
    )


@app.get("/health/workers")
def workers_health() -> Dict[str, Any]:
    """
    Worker pool status probe: inspects child worker processes and crash-loop backoff state.
    """
    statuses = worker_manager.get_status()
    return {
        "status": "ok",
        **statuses,
    }


@app.get("/health/alerts")
def alerts_endpoint(active_only: bool = False) -> Dict[str, Any]:
    """
    Operational alerts endpoint: inspects active and resolved system alerts.
    Sanitized: no credentials, no patient PII, strictly operational metadata.
    """
    from app.core.metrics import metrics_collector
    ok, _ = check_database_connection()
    health_eval = alert_manager.evaluate_system_health(
        metrics_summary=metrics_collector.get_summary(),
        db_healthy=ok,
        db_latency_ms=metrics_collector.last_db_ping_latency_ms,
        worker_statuses=worker_manager.get_status(),
    )
    alerts = alert_manager.get_alerts(active_only=active_only)
    return {
        "timestamp": health_eval["timestamp"],
        "overall_status": health_eval["overall_status"],
        "summary": health_eval["summary"],
        "alerts": alerts,
    }


@app.get("/health/metrics")
def metrics_endpoint() -> Dict[str, Any]:
    """
    Lightweight operational metrics endpoint for production observability.
    Sanitized: contains no credentials, no patient PII, no raw payloads.
    """
    from app.core.metrics import metrics_collector
    return metrics_collector.get_summary()


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "FetalAI backend is running",
    }


# =========================================================
# APPLICATION ENTRY POINT
# =========================================================

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
