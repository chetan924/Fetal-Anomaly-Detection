import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# ALERT ENUMS
# ============================================================

class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    FIRING = "FIRING"
    RESOLVED = "RESOLVED"


class ServiceHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


# ============================================================
# ALERT MODEL
# ============================================================

class Alert:
    """
    Represents an operational alert with occurrence counting and timestamps.
    """

    def __init__(
        self,
        fingerprint: str,
        rule_name: str,
        severity: AlertSeverity,
        title: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        now_iso = datetime.now(timezone.utc).isoformat()
        self.fingerprint = fingerprint
        self.rule_name = rule_name
        self.severity = severity
        self.status = AlertStatus.FIRING
        self.title = title
        self.description = description
        self.details = details or {}
        self.count = 1
        self.first_seen = now_iso
        self.last_seen = now_iso
        self.last_notified_at = time.time()
        self.resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "rule_name": self.rule_name,
            "severity": self.severity.value if isinstance(self.severity, AlertSeverity) else self.severity,
            "status": self.status.value if isinstance(self.status, AlertStatus) else self.status,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "resolved_at": self.resolved_at,
        }


# ============================================================
# ALERT MANAGER
# ============================================================

class AlertManager:
    """
    Provider-neutral in-memory Alert & Health Evaluation Engine for FetalAI.
    Thread-safe, bounded memory, deduplication, cooldown intervals, and auto-resolution.
    """

    def __init__(
        self,
        cooldown_seconds: float = 60.0,
        max_alerts: int = 50,
    ):
        self._lock = threading.Lock()
        self.cooldown_seconds = cooldown_seconds
        self.max_alerts = max_alerts
        self._alerts: Dict[str, Alert] = {}

    def _generate_fingerprint(self, rule_name: str, details: Optional[Dict[str, Any]] = None) -> str:
        if details and "target" in details:
            return f"{rule_name}:{details['target']}"
        if details and "worker" in details:
            return f"{rule_name}:{details['worker']}"
        return rule_name

    def fire(
        self,
        rule_name: str,
        severity: AlertSeverity,
        title: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        fingerprint: Optional[str] = None,
    ) -> Alert:
        """
        Fires an alert. Deduplicates against existing firing alerts with same fingerprint.
        """
        fp = fingerprint or self._generate_fingerprint(rule_name, details)
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        should_log = False

        with self._lock:
            if fp in self._alerts:
                alert = self._alerts[fp]
                if alert.status == AlertStatus.FIRING:
                    alert.count += 1
                    alert.last_seen = now_iso
                    alert.details = details or alert.details
                    alert.description = description
                    # Only log if cooldown passed
                    if (now - alert.last_notified_at) >= self.cooldown_seconds:
                        alert.last_notified_at = now
                        should_log = True
                    return alert
                else:
                    # Alert was previously resolved, re-fire
                    alert.status = AlertStatus.FIRING
                    alert.severity = severity
                    alert.title = title
                    alert.description = description
                    alert.details = details or {}
                    alert.count += 1
                    alert.last_seen = now_iso
                    alert.resolved_at = None
                    alert.last_notified_at = now
                    should_log = True
                    return alert
            else:
                # Evict oldest resolved alert if at limit, or oldest alert if none resolved
                if len(self._alerts) >= self.max_alerts:
                    self._evict_oldest()

                alert = Alert(
                    fingerprint=fp,
                    rule_name=rule_name,
                    severity=severity,
                    title=title,
                    description=description,
                    details=details,
                )
                self._alerts[fp] = alert
                should_log = True

        if should_log:
            try:
                from app.core.observability_logger import emit_structured_log
                emit_structured_log(
                    "ERROR" if severity == AlertSeverity.CRITICAL else "WARN",
                    "ALERT_FIRED",
                    f"[{severity.value}] {title}: {description}",
                    details={
                        "fingerprint": fp,
                        "rule_name": rule_name,
                        "severity": severity.value if isinstance(severity, AlertSeverity) else severity,
                        **(details or {}),
                    },
                )
            except Exception:
                pass

        return alert

    def resolve(self, fingerprint: str, reason: Optional[str] = None) -> Optional[Alert]:
        """
        Transitions a firing alert to RESOLVED status.
        """
        with self._lock:
            if fingerprint not in self._alerts:
                return None
            alert = self._alerts[fingerprint]
            if alert.status == AlertStatus.RESOLVED:
                return alert

            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc).isoformat()
            if reason:
                alert.details["resolve_reason"] = reason

        try:
            from app.core.observability_logger import emit_structured_log
            emit_structured_log(
                "INFO",
                "ALERT_RESOLVED",
                f"[RESOLVED] {alert.title} - {reason or 'Condition returned to normal'}",
                details={"fingerprint": fingerprint, "rule_name": alert.rule_name},
            )
        except Exception:
            pass

        return alert

    def _evict_oldest(self) -> None:
        """
        Evicts resolved alerts first, then oldest last_seen alerts.
        """
        resolved_fps = [fp for fp, a in self._alerts.items() if a.status == AlertStatus.RESOLVED]
        if resolved_fps:
            oldest_fp = min(resolved_fps, key=lambda fp: self._alerts[fp].last_seen)
            del self._alerts[oldest_fp]
            return

        if self._alerts:
            oldest_fp = min(self._alerts.keys(), key=lambda fp: self._alerts[fp].last_seen)
            del self._alerts[oldest_fp]

    def get_alerts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            alerts_list = list(self._alerts.values())
            if active_only:
                alerts_list = [a for a in alerts_list if a.status == AlertStatus.FIRING]
            return [a.to_dict() for a in sorted(alerts_list, key=lambda a: a.last_seen, reverse=True)]

    def evaluate_system_health(
        self,
        metrics_summary: Dict[str, Any],
        db_healthy: bool,
        db_latency_ms: float = 0.0,
        worker_statuses: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive system health evaluation:
        Checks database, memory, slow requests, and worker pool.
        Fires or resolves appropriate alerts and determines overall health status.
        """
        # 1. Database Health
        db_fp = "database_connectivity"
        if not db_healthy:
            self.fire(
                rule_name="database_connectivity",
                severity=AlertSeverity.CRITICAL,
                title="Database Connectivity Failure",
                description="Unable to connect to PostgreSQL database via connection pool pre-ping.",
                details={"latency_ms": db_latency_ms},
                fingerprint=db_fp,
            )
        else:
            self.resolve(db_fp, reason=f"Database ping healthy ({db_latency_ms:.2f}ms)")

        # 2. Memory Pressure
        mem = metrics_summary.get("memory", {})
        mem_fp = "high_memory_pressure"
        if mem.get("is_high_memory_pressure", False):
            self.fire(
                rule_name="high_memory_pressure",
                severity=AlertSeverity.WARNING,
                title="High Gateway Memory Pressure",
                description=f"Gateway process RSS memory ({mem.get('rss_mb', 0)}MB) exceeded threshold ({mem.get('high_memory_threshold_mb', 400)}MB).",
                details={"rss_mb": mem.get("rss_mb", 0), "threshold_mb": mem.get("high_memory_threshold_mb", 400)},
                fingerprint=mem_fp,
            )
        else:
            self.resolve(mem_fp, reason="Memory consumption within normal operating limits")

        # 3. Worker Crash Loops & Errors
        if worker_statuses and "workers" in worker_statuses:
            for w_name, w_info in worker_statuses["workers"].items():
                w_fp = f"worker_crash_loop:{w_name}"
                state = w_info.get("state")
                crash_count = w_info.get("crash_count", 0)
                in_backoff = state in ("crash_loop_backoff", "unhealthy") and crash_count >= 3

                if in_backoff:
                    self.fire(
                        rule_name="worker_crash_loop",
                        severity=AlertSeverity.CRITICAL,
                        title=f"Worker Crash-Loop: {w_name}",
                        description=f"Worker '{w_name}' crashed {crash_count} times in rapid succession. Placed in backoff.",
                        details={"worker": w_name, "state": state, "crash_count": crash_count, "port": w_info.get("port")},
                        fingerprint=w_fp,
                    )
                elif state == "healthy":
                    self.resolve(w_fp, reason=f"Worker '{w_name}' running normally")

        # 4. Aggregate Overall Status
        with self._lock:
            firing_alerts = [a for a in self._alerts.values() if a.status == AlertStatus.FIRING]
            critical_count = sum(1 for a in firing_alerts if a.severity == AlertSeverity.CRITICAL)
            warning_count = sum(1 for a in firing_alerts if a.severity == AlertSeverity.WARNING)

            if critical_count > 0 or not db_healthy:
                overall_status = ServiceHealthStatus.UNAVAILABLE
            elif warning_count > 0 or mem.get("is_high_memory_pressure", False):
                overall_status = ServiceHealthStatus.DEGRADED
            else:
                overall_status = ServiceHealthStatus.HEALTHY

            return {
                "overall_status": overall_status.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "critical_alerts": critical_count,
                    "warning_alerts": warning_count,
                    "total_firing": len(firing_alerts),
                },
                "active_alerts": [a.to_dict() for a in firing_alerts],
            }

    def clear(self) -> None:
        """
        Clears all in-memory alerts (used for testing and resets).
        """
        with self._lock:
            self._alerts.clear()


alert_manager = AlertManager()
