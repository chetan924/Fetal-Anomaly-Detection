import os
import sys
import time
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False


class MetricsCollector:
    """
    Thread-safe, bounded in-memory metrics registry for FetalAI.
    Zero heavy dependencies, negligible runtime overhead, memory-bounded.
    """

    def __init__(
        self,
        slow_threshold_ms: float = 2000.0,
        high_memory_threshold_mb: float = 400.0,
        max_recent_events: int = 100,
    ):
        self._lock = threading.Lock()
        self.slow_threshold_ms = slow_threshold_ms
        self.high_memory_threshold_mb = high_memory_threshold_mb
        self.start_time = time.time()

        # Request Metrics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.status_distribution: Dict[str, int] = {}
        self.endpoint_metrics: Dict[str, Dict[str, Any]] = {}
        self.slow_requests_count = 0
        self.recent_slow_requests = deque(maxlen=max_recent_events)

        # Worker & Model Metrics
        self.model_metrics: Dict[str, Dict[str, Any]] = {
            "plane": self._init_model_stats(),
            "spine": self._init_model_stats(),
            "brain": self._init_model_stats(),
            "lung": self._init_model_stats(),
            "bone": self._init_model_stats(),
            "placenta": self._init_model_stats(),
            "face": self._init_model_stats(),
            "heart": self._init_model_stats(),
            "kidney": self._init_model_stats(disabled=True),
        }

        # Comprehensive Pipeline Metrics
        self.pipeline_total = 0
        self.pipeline_completed = 0
        self.pipeline_partial = 0
        self.pipeline_failed = 0
        self.pipeline_total_duration_ms = 0.0
        self.pipeline_max_duration_ms = 0.0

        # Session Metrics
        self.session_transitions: Dict[str, int] = {
            "draft": 0,
            "ready": 0,
            "processing": 0,
            "completed": 0,
            "partial": 0,
            "failed": 0,
            "interrupted": 0,
        }
        self.idempotent_cache_hits = 0
        self.stale_sessions_recovered = 0

        # Report & PDF Metrics
        self.reports_generated = 0
        self.report_generation_duration_ms = 0.0
        self.pdf_generated = 0
        self.pdf_generation_duration_ms = 0.0
        self.pdf_stream_failures = 0
        self.report_lookup_failures = 0
        self.report_authz_denials = 0

        # Database Health Metrics
        self.db_pings_total = 0
        self.db_pings_success = 0
        self.db_pings_failed = 0
        self.last_db_ping_latency_ms = 0.0
        self.last_db_ping_status = "unknown"
        self.last_db_ping_timestamp: Optional[str] = None

        # Security Operational Counters
        self.security_events: Dict[str, int] = {
            "auth_login_success": 0,
            "auth_login_failure": 0,
            "authz_denied": 0,
            "jwt_invalid": 0,
            "jwt_expired": 0,
            "rate_limit_exceeded": 0,
            "upload_invalid_ext": 0,
            "upload_malformed": 0,
            "path_traversal_blocked": 0,
        }

    def _init_model_stats(self, disabled: bool = False) -> Dict[str, Any]:
        return {
            "disabled": disabled,
            "requests": 0,
            "success": 0,
            "failures": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "startup_count": 0,
            "restart_count": 0,
            "crash_count": 0,
            "reap_count": 0,
            "last_startup_duration_ms": 0.0,
            "last_used_at": None,
        }

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Records an HTTP request execution. Returns True if this was a slow request.
        """
        is_slow = duration_ms >= self.slow_threshold_ms
        with self._lock:
            self.total_requests += 1
            if status_code < 400:
                self.successful_requests += 1
            else:
                self.failed_requests += 1

            status_key = str(status_code)
            self.status_distribution[status_key] = (
                self.status_distribution.get(status_key, 0) + 1
            )

            # Endpoint aggregation
            ep_key = f"{method} {path}"
            if ep_key not in self.endpoint_metrics:
                self.endpoint_metrics[ep_key] = {
                    "count": 0,
                    "total_ms": 0.0,
                    "min_ms": duration_ms,
                    "max_ms": duration_ms,
                    "avg_ms": duration_ms,
                    "errors": 0,
                }
            ep = self.endpoint_metrics[ep_key]
            ep["count"] += 1
            ep["total_ms"] += duration_ms
            ep["min_ms"] = min(ep["min_ms"], duration_ms)
            ep["max_ms"] = max(ep["max_ms"], duration_ms)
            ep["avg_ms"] = round(ep["total_ms"] / ep["count"], 2)
            if status_code >= 400:
                ep["errors"] += 1

            if is_slow:
                self.slow_requests_count += 1
                self.recent_slow_requests.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                })

        return is_slow

    def record_worker_startup(self, model_name: str, duration_ms: float, success: bool = True) -> None:
        with self._lock:
            if model_name not in self.model_metrics:
                self.model_metrics[model_name] = self._init_model_stats()
            m = self.model_metrics[model_name]
            m["startup_count"] += 1
            m["last_startup_duration_ms"] = round(duration_ms, 2)
            if not success:
                m["failures"] += 1

    def record_worker_crash(self, model_name: str) -> None:
        with self._lock:
            if model_name in self.model_metrics:
                self.model_metrics[model_name]["crash_count"] += 1

    def record_worker_restart(self, model_name: str) -> None:
        with self._lock:
            if model_name in self.model_metrics:
                self.model_metrics[model_name]["restart_count"] += 1

    def record_worker_reap(self, model_name: str) -> None:
        with self._lock:
            if model_name in self.model_metrics:
                self.model_metrics[model_name]["reap_count"] += 1

    def record_inference(
        self,
        model_name: str,
        duration_ms: float,
        success: bool = True,
        is_timeout: bool = False,
    ) -> None:
        with self._lock:
            if model_name not in self.model_metrics:
                self.model_metrics[model_name] = self._init_model_stats()
            m = self.model_metrics[model_name]
            m["requests"] += 1
            m["last_used_at"] = datetime.now(timezone.utc).isoformat()
            if success:
                m["success"] += 1
                m["total_latency_ms"] += duration_ms
                m["max_latency_ms"] = max(m["max_latency_ms"], duration_ms)
                if m["success"] > 0:
                    m["avg_latency_ms"] = round(m["total_latency_ms"] / m["success"], 2)
            else:
                m["failures"] += 1
                if is_timeout:
                    m["timeouts"] += 1

    def record_comprehensive_analysis(
        self,
        duration_ms: float,
        status: str,
        requested_count: int,
        completed_count: int,
        failed_count: int,
        unavailable_count: int,
    ) -> None:
        with self._lock:
            self.pipeline_total += 1
            self.pipeline_total_duration_ms += duration_ms
            self.pipeline_max_duration_ms = max(self.pipeline_max_duration_ms, duration_ms)
            if status == "completed":
                self.pipeline_completed += 1
            elif status == "partial":
                self.pipeline_partial += 1
            else:
                self.pipeline_failed += 1

    def record_session_transition(self, new_status: str) -> None:
        with self._lock:
            if new_status in self.session_transitions:
                self.session_transitions[new_status] += 1
            else:
                self.session_transitions[new_status] = 1

    def record_idempotent_hit(self) -> None:
        with self._lock:
            self.idempotent_cache_hits += 1

    def record_stale_recovery(self, count: int = 1) -> None:
        with self._lock:
            self.stale_sessions_recovered += count

    def record_report_generation(self, duration_ms: float, success: bool = True) -> None:
        with self._lock:
            if success:
                self.reports_generated += 1
                self.report_generation_duration_ms += duration_ms

    def record_pdf_generation(self, duration_ms: float, success: bool = True) -> None:
        with self._lock:
            if success:
                self.pdf_generated += 1
                self.pdf_generation_duration_ms += duration_ms
            else:
                self.pdf_stream_failures += 1

    def record_pdf_failure(self) -> None:
        with self._lock:
            self.pdf_stream_failures += 1

    def record_report_lookup_failure(self) -> None:
        with self._lock:
            self.report_lookup_failures += 1

    def record_report_authz_denial(self) -> None:
        with self._lock:
            self.report_authz_denials += 1

    def record_db_ping(self, latency_ms: float, success: bool = True, error: Optional[str] = None) -> None:
        with self._lock:
            self.db_pings_total += 1
            self.last_db_ping_latency_ms = round(latency_ms, 2)
            self.last_db_ping_timestamp = datetime.now(timezone.utc).isoformat()
            if success:
                self.db_pings_success += 1
                self.last_db_ping_status = "connected"
            else:
                self.db_pings_failed += 1
                self.last_db_ping_status = "disconnected"

    def record_security_event(self, event_type: str, status: str = "SUCCESS") -> None:
        with self._lock:
            ev_lower = event_type.lower()
            if "login" in ev_lower and status.upper() == "SUCCESS":
                self.security_events["auth_login_success"] += 1
            elif "login" in ev_lower and status.upper() in ("FAILURE", "DENIED"):
                self.security_events["auth_login_failure"] += 1
            elif "authz_denied" in ev_lower or status.upper() == "DENIED":
                self.security_events["authz_denied"] += 1
            elif "rate_limit" in ev_lower:
                self.security_events["rate_limit_exceeded"] += 1
            elif "invalid_ext" in ev_lower:
                self.security_events["upload_invalid_ext"] += 1
            elif "malformed" in ev_lower:
                self.security_events["upload_malformed"] += 1
            elif "traversal" in ev_lower:
                self.security_events["path_traversal_blocked"] += 1

    def get_memory_metrics(self) -> Dict[str, Any]:
        """
        Retrieves current process RSS memory in bytes and MB.
        """
        rss_bytes = 0
        rss_mb = 0.0
        if HAS_PSUTIL and psutil is not None:
            try:
                proc = psutil.Process()
                mem = proc.memory_info()
                rss_bytes = mem.rss
                rss_mb = round(rss_bytes / (1024 * 1024), 2)
            except Exception:
                pass

        is_high = rss_mb >= self.high_memory_threshold_mb
        return {
            "rss_bytes": rss_bytes,
            "rss_mb": rss_mb,
            "high_memory_threshold_mb": self.high_memory_threshold_mb,
            "is_high_memory_pressure": is_high,
            "uptime_seconds": round(time.time() - self.start_time, 2),
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns a clean, sanitized dictionary of operational metrics.
        No passwords, no patient PII, no internal file paths.
        """
        with self._lock:
            now_utc = datetime.now(timezone.utc).isoformat()
            mem = self.get_memory_metrics()

            avg_pipeline_ms = (
                round(self.pipeline_total_duration_ms / self.pipeline_total, 2)
                if self.pipeline_total > 0
                else 0.0
            )

            avg_report_ms = (
                round(self.report_generation_duration_ms / self.reports_generated, 2)
                if self.reports_generated > 0
                else 0.0
            )

            avg_pdf_ms = (
                round(self.pdf_generation_duration_ms / self.pdf_generated, 2)
                if self.pdf_generated > 0
                else 0.0
            )

            return {
                "timestamp": now_utc,
                "service": "fetalai-gateway",
                "uptime_seconds": mem["uptime_seconds"],
                "memory": mem,
                "requests": {
                    "total": self.total_requests,
                    "successful": self.successful_requests,
                    "failed": self.failed_requests,
                    "status_distribution": dict(self.status_distribution),
                    "slow_requests_count": self.slow_requests_count,
                    "slow_threshold_ms": self.slow_threshold_ms,
                    "recent_slow_requests": list(self.recent_slow_requests),
                    "top_endpoints": {
                        k: v for k, v in sorted(
                            self.endpoint_metrics.items(),
                            key=lambda item: item[1]["count"],
                            reverse=True
                        )[:15]
                    },
                },
                "models": {k: dict(v) for k, v in self.model_metrics.items()},
                "comprehensive_pipeline": {
                    "total_runs": self.pipeline_total,
                    "completed": self.pipeline_completed,
                    "partial": self.pipeline_partial,
                    "failed": self.pipeline_failed,
                    "avg_duration_ms": avg_pipeline_ms,
                    "max_duration_ms": round(self.pipeline_max_duration_ms, 2),
                },
                "sessions": {
                    "state_transitions": dict(self.session_transitions),
                    "idempotent_cache_hits": self.idempotent_cache_hits,
                    "stale_sessions_recovered": self.stale_sessions_recovered,
                },
                "reports": {
                    "reports_generated": self.reports_generated,
                    "avg_report_duration_ms": avg_report_ms,
                    "pdf_generated": self.pdf_generated,
                    "avg_pdf_duration_ms": avg_pdf_ms,
                    "pdf_stream_failures": self.pdf_stream_failures,
                    "report_lookup_failures": self.report_lookup_failures,
                    "report_authz_denials": self.report_authz_denials,
                },
                "database": {
                    "total_pings": self.db_pings_total,
                    "successful_pings": self.db_pings_success,
                    "failed_pings": self.db_pings_failed,
                    "last_ping_latency_ms": self.last_db_ping_latency_ms,
                    "last_ping_status": self.last_db_ping_status,
                    "last_ping_timestamp": self.last_db_ping_timestamp,
                },
                "security": dict(self.security_events),
            }


metrics_collector = MetricsCollector()
