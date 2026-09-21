import asyncio
import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import (
    INFERENCE_TIMEOUT_SECONDS,
    WORKER_HEALTH_TIMEOUT_SECONDS,
    WORKER_MAX_RETRIES,
)
from app.inference.model_registry import (
    get_worker_config,
)
from app.inference.response_models import (
    ErrorCode,
    InferenceException,
)
from app.inference.worker_manager import (
    WorkerState,
    worker_manager,
)

logger = logging.getLogger("fetalai.worker_client")


class WorkerClient:
    """
    Hardened HTTP client used by FastAPI to communicate
    with isolated ML workers.

    Features:
    - On-demand worker startup via WorkerLifecycleManager
    - Request lease tracking preventing premature idle termination
    - Single transient retry on connection drops
    - Request ID (X-Request-ID) forwarding
    - Sanitized error normalization (no internal port/path leakage)
    - Configurable timeouts
    """

    def __init__(
        self,
        timeout: float = INFERENCE_TIMEOUT_SECONDS,
        health_timeout: float = WORKER_HEALTH_TIMEOUT_SECONDS,
        max_retries: int = WORKER_MAX_RETRIES,
    ):
        self.timeout = timeout
        self.health_timeout = health_timeout
        self.max_retries = max(0, max_retries)

    async def health(
        self,
        model_name: str,
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        config = get_worker_config(model_name)

        if config.get("disabled"):
            return {
                "status": "disabled",
                "worker": model_name,
                "reason": config.get("disabled_reason", "model unavailable"),
            }

        info = worker_manager.get_info(model_name)

        if auto_start and info.state != WorkerState.HEALTHY:
            try:
                await worker_manager.ensure_worker_running(model_name)
            except Exception as exc:
                return {
                    "status": "error",
                    "worker": model_name,
                    "error": str(exc),
                }

        # If not running and auto_start was false, return current state passively
        if not worker_manager.is_process_alive(info) and info.state != WorkerState.HEALTHY:
            return {
                "status": info.state.value,
                "worker": model_name,
                "pid": info.pid,
                "model_loaded": False,
            }

        url = config["url"] + "/health"

        try:
            async with httpx.AsyncClient(timeout=self.health_timeout) as client:
                response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as exc:
            return {
                "status": "unavailable",
                "worker": model_name,
                "error": "Worker service is currently unreachable.",
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "worker": model_name,
                "http_status": exc.response.status_code,
                "error": "Worker health check failed.",
            }

    async def predict(
        self,
        model_name: str,
        filename: str,
        content: bytes,
        content_type: str,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        config = get_worker_config(model_name)

        if config.get("disabled"):
            raise InferenceException(
                status_code=503,
                code=ErrorCode.WORKER_DISABLED,
                message=(
                    f"{model_name.capitalize()} AI worker is currently disabled "
                    f"({config.get('disabled_reason', 'model unavailable')})."
                ),
                model=model_name,
            )

        if not content:
            raise InferenceException(
                status_code=400,
                code=ErrorCode.VALIDATION_ERROR,
                message="Uploaded file is empty.",
                model=model_name,
            )

        # Ensure worker process is running and healthy
        try:
            await worker_manager.ensure_worker_running(model_name)
        except Exception as exc:
            logger.error(
                "Worker startup failure: model=%s request_id=%s error=%s",
                model_name,
                request_id,
                exc,
            )
            raise InferenceException(
                status_code=503,
                code=ErrorCode.WORKER_STARTUP_FAILED,
                message=f"Failed to start {model_name} AI worker.",
                model=model_name,
            ) from exc

        url = config["url"] + config["endpoint"]

        files = {
            "file": (
                filename,
                content,
                content_type,
            )
        }

        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id

        # Hold a lease during inference to prevent idle shutdown
        async with worker_manager.lease(model_name):
            attempts = 0
            max_attempts = 1 + self.max_retries
            t_start = time.time()

            while attempts < max_attempts:
                attempts += 1
                try:
                    async with httpx.AsyncClient(
                        timeout=self.timeout
                    ) as client:
                        response = await client.post(
                            url,
                            files=files,
                            headers=headers,
                        )
                    response.raise_for_status()
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_inference(model_name, duration_ms, success=True)
                        emit_structured_log(
                            "INFO",
                            "INFERENCE_SUCCESS",
                            f"Inference on {model_name} succeeded in {duration_ms:.2f}ms",
                            request_id=request_id,
                            model=model_name,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        pass
                    return response.json()

                except httpx.TimeoutException as exc:
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    logger.warning(
                        "Worker timeout: model=%s request_id=%s attempt=%d/%d",
                        model_name,
                        request_id,
                        attempts,
                        max_attempts,
                    )
                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_inference(model_name, duration_ms, success=False, is_timeout=True)
                        emit_structured_log(
                            "WARN",
                            "INFERENCE_TIMEOUT",
                            f"Inference on {model_name} timed out after {self.timeout}s",
                            request_id=request_id,
                            model=model_name,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        pass
                    raise InferenceException(
                        status_code=504,
                        code=ErrorCode.WORKER_TIMEOUT,
                        message=f"{model_name.capitalize()} AI analysis timed out after {self.timeout} seconds.",
                        model=model_name,
                    ) from exc

                except (httpx.ConnectError, httpx.NetworkError) as exc:
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    logger.warning(
                        "Worker connection drop: model=%s request_id=%s attempt=%d/%d error=%s",
                        model_name,
                        request_id,
                        attempts,
                        max_attempts,
                        exc,
                    )
                    if attempts < max_attempts:
                        await asyncio.sleep(0.5)
                        continue

                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_inference(model_name, duration_ms, success=False, is_timeout=False)
                        emit_structured_log(
                            "ERROR",
                            "INFERENCE_CONNECTION_ERROR",
                            f"Connection to {model_name} AI worker failed",
                            request_id=request_id,
                            model=model_name,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        pass
                    raise InferenceException(
                        status_code=503,
                        code=ErrorCode.WORKER_UNAVAILABLE,
                        message=f"{model_name.capitalize()} AI worker is currently unavailable. Please try again.",
                        model=model_name,
                    ) from exc

                except httpx.HTTPStatusError as exc:
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    logger.error(
                        "Worker HTTP error: model=%s request_id=%s status=%d",
                        model_name,
                        request_id,
                        exc.response.status_code,
                    )
                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_inference(model_name, duration_ms, success=False, is_timeout=False)
                        emit_structured_log(
                            "ERROR",
                            "INFERENCE_HTTP_ERROR",
                            f"Worker for {model_name} returned status {exc.response.status_code}",
                            request_id=request_id,
                            model=model_name,
                            status_code=exc.response.status_code,
                            duration_ms=duration_ms,
                        )
                    except Exception:
                        pass
                    raise InferenceException(
                        status_code=502,
                        code=ErrorCode.INFERENCE_FAILED,
                        message=f"{model_name.capitalize()} AI worker returned an error during analysis.",
                        model=model_name,
                    ) from exc

                except ValueError as exc:
                    duration_ms = round((time.time() - t_start) * 1000, 2)
                    logger.error(
                        "Worker JSON decode error: model=%s request_id=%s error=%s",
                        model_name,
                        request_id,
                        exc,
                    )
                    try:
                        from app.core.metrics import metrics_collector
                        metrics_collector.record_inference(model_name, duration_ms, success=False, is_timeout=False)
                    except Exception:
                        pass
                    raise InferenceException(
                        status_code=502,
                        code=ErrorCode.INFERENCE_FAILED,
                        message=f"Invalid response payload received from {model_name} AI worker.",
                        model=model_name,
                    ) from exc


worker_client = WorkerClient()