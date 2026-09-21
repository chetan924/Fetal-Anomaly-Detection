import asyncio
import os
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.inference.model_registry import (
    MODEL_WORKERS,
    get_all_worker_configs,
    get_worker_config,
)

# ============================================================
# CONFIGURATION
# ============================================================

BACKEND_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = BACKEND_ROOT / "storage" / "worker_logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_IDLE_TIMEOUT = float(os.getenv("WORKER_IDLE_TIMEOUT_SECONDS", "300"))
DEFAULT_STARTUP_TIMEOUT = float(os.getenv("WORKER_STARTUP_TIMEOUT_SECONDS", "60"))
AUTO_START_ENABLED = os.getenv("WORKER_AUTO_START", "true").lower() in ("1", "true", "yes")
REAPER_INTERVAL = float(os.getenv("WORKER_REAPER_INTERVAL_SECONDS", "5"))

# Crash-loop protection constants
MAX_RESTART_ATTEMPTS = int(os.getenv("WORKER_MAX_RESTART_ATTEMPTS", "3"))
RESTART_WINDOW_SECONDS = float(os.getenv("WORKER_RESTART_WINDOW_SECONDS", "60"))
CRASH_LOOP_BACKOFF_SECONDS = float(os.getenv("WORKER_BACKOFF_SECONDS", "30"))


# ============================================================
# WORKER STATES
# ============================================================

class WorkerState(str, Enum):
    NOT_STARTED = "not_started"
    STARTING = "starting"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"
    CRASH_LOOP_BACKOFF = "crash_loop_backoff"
    DISABLED = "disabled"


# ============================================================
# WORKER PROCESS INFO
# ============================================================

class WorkerProcessInfo:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name: str = name
        self.config: Dict[str, Any] = config
        self.port: int = int(config.get("port", 0))
        self.disabled: bool = bool(config.get("disabled", False))
        self.disabled_reason: Optional[str] = config.get("disabled_reason")
        self.process: Optional[subprocess.Popen] = None
        self.pid: Optional[int] = None
        self.state: WorkerState = (
            WorkerState.DISABLED if self.disabled else WorkerState.NOT_STARTED
        )
        self.active_requests: int = 0
        self.last_used_at: Optional[float] = None
        self.started_at: Optional[float] = None
        self.last_error: Optional[str] = None
        self.lock: asyncio.Lock = asyncio.Lock()
        self.log_file: Path = LOGS_DIR / f"{name}_worker.log"

        # Crash-loop tracking
        self.recent_crashes: List[float] = []
        self.backoff_until: Optional[float] = None
        self.crash_loop_detected: bool = False

    def record_crash(self, timestamp: float) -> bool:
        """
        Records a crash timestamp, cleans up timestamps outside the window,
        and triggers crash-loop backoff if threshold is reached.
        Returns True if crash loop triggered.
        """
        self.recent_crashes.append(timestamp)
        cutoff = timestamp - RESTART_WINDOW_SECONDS
        self.recent_crashes = [t for t in self.recent_crashes if t >= cutoff]

        if len(self.recent_crashes) >= MAX_RESTART_ATTEMPTS:
            self.crash_loop_detected = True
            self.backoff_until = timestamp + CRASH_LOOP_BACKOFF_SECONDS
            self.state = WorkerState.CRASH_LOOP_BACKOFF
            return True
        return False

    def is_in_backoff(self, current_time: float) -> bool:
        """
        Returns True if the worker is currently within a crash-loop cooldown.
        Automatically clears backoff once current_time exceeds backoff_until.
        """
        if self.backoff_until is not None:
            if current_time < self.backoff_until:
                return True
            # Backoff window expired: reset state
            self.backoff_until = None
            self.crash_loop_detected = False
            if self.state == WorkerState.CRASH_LOOP_BACKOFF:
                self.state = WorkerState.STOPPED
        return False

    def reset_crash_loop(self) -> None:
        """
        Manually clears crash-loop state and backoff timers.
        """
        self.recent_crashes.clear()
        self.backoff_until = None
        self.crash_loop_detected = False
        if self.state == WorkerState.CRASH_LOOP_BACKOFF:
            self.state = WorkerState.STOPPED


# ============================================================
# WORKER LIFECYCLE MANAGER
# ============================================================

class WorkerLifecycleManager:
    """
    Process-level Worker Lifecycle Manager with Crash-Loop Mitigation.

    Starts specialized ML worker processes on demand,
    reuses loaded models across requests, monitors in-flight
    requests, prevents rapid crash-loop thrashing, and terminates idle worker processes.
    """

    def __init__(
        self,
        idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
        startup_timeout: float = DEFAULT_STARTUP_TIMEOUT,
        auto_start: bool = AUTO_START_ENABLED,
    ):
        self.idle_timeout = idle_timeout
        self.startup_timeout = startup_timeout
        self.auto_start = auto_start
        self._workers: Dict[str, WorkerProcessInfo] = {}
        self._reaper_task: Optional[asyncio.Task] = None
        self._is_running = True
        self._init_workers()

    def _init_workers(self) -> None:
        configs = get_all_worker_configs()
        for name, cfg in configs.items():
            self._workers[name] = WorkerProcessInfo(name, cfg)

    def get_info(self, model_name: str) -> WorkerProcessInfo:
        if model_name not in self._workers:
            cfg = get_worker_config(model_name)
            self._workers[model_name] = WorkerProcessInfo(model_name, cfg)
        return self._workers[model_name]

    def is_process_alive(self, info: WorkerProcessInfo) -> bool:
        if info.process is None:
            return False
        return info.process.poll() is None

    async def ensure_worker_running(self, model_name: str) -> None:
        info = self.get_info(model_name)

        if info.disabled:
            raise RuntimeError(
                f"Worker '{model_name}' is disabled ({info.disabled_reason or 'model unavailable'})."
            )

        now = time.time()
        if info.is_in_backoff(now):
            remaining = round((info.backoff_until or now) - now, 1)
            raise RuntimeError(
                f"Worker '{model_name}' is in crash-loop backoff ({remaining}s cooldown remaining). Protection active."
            )

        # Fast path: already healthy and process is alive
        if info.state == WorkerState.HEALTHY and self.is_process_alive(info):
            return

        async with info.lock:
            now = time.time()
            if info.is_in_backoff(now):
                remaining = round((info.backoff_until or now) - now, 1)
                raise RuntimeError(
                    f"Worker '{model_name}' is in crash-loop backoff ({remaining}s cooldown remaining). Protection active."
                )

            # Re-check inside lock
            if info.state == WorkerState.HEALTHY and self.is_process_alive(info):
                return

            # Check if process crashed
            if info.process is not None and info.process.poll() is not None:
                info.state = WorkerState.CRASHED
                info.pid = None
                info.process = None
                is_loop = info.record_crash(now)
                if is_loop:
                    self._fire_crash_loop_alert(model_name, info)
                    raise RuntimeError(
                        f"Worker '{model_name}' entered crash-loop backoff ({CRASH_LOOP_BACKOFF_SECONDS}s cooldown)."
                    )

            # Spawn process
            info.state = WorkerState.STARTING
            info.last_error = None
            cfg = info.config

            python_cmd: List[str] = list(cfg.get("python_cmd", ["py", "-3.10"]))
            module: str = str(cfg.get("module", f"app.workers.{model_name}.worker:app"))
            port: int = info.port

            cmd = python_cmd + [
                "-m",
                "uvicorn",
                module,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ]

            log_fp = open(info.log_file, "w", encoding="utf-8", buffering=1)

            try:
                info.process = subprocess.Popen(
                    cmd,
                    cwd=str(BACKEND_ROOT),
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    env=os.environ.copy(),
                )
                info.pid = info.process.pid
                info.started_at = time.time()
            except Exception as exc:
                info.state = WorkerState.UNHEALTHY
                info.last_error = f"Failed to spawn worker process: {exc}"
                info.record_crash(time.time())
                try:
                    log_fp.close()
                except Exception:
                    pass
                raise RuntimeError(
                    f"Could not start worker '{model_name}': {exc}"
                ) from exc

            # Poll /health until worker responds healthy or timeout occurs
            health_url = f"{cfg['url']}/health"
            start_time = time.time()
            is_ready = False

            while time.time() - start_time < self.startup_timeout:
                if info.process.poll() is not None:
                    # Process died during startup
                    exit_code = info.process.returncode
                    info.state = WorkerState.CRASHED
                    info.pid = None
                    info.process = None
                    is_loop = info.record_crash(time.time())
                    log_tail = self._read_log_tail(info.log_file)
                    err_msg = (
                        f"Worker '{model_name}' exited prematurely with exit code {exit_code}.\n"
                        f"Recent logs:\n{log_tail}"
                    )
                    info.last_error = err_msg
                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_worker_crash(model_name)
                        emit_structured_log(
                            "ERROR",
                            "WORKER_CRASH",
                            f"Worker '{model_name}' exited prematurely with exit code {exit_code}",
                            worker=model_name,
                            details={"exit_code": exit_code},
                        )
                    except Exception:
                        pass

                    if is_loop:
                        self._fire_crash_loop_alert(model_name, info)

                    raise RuntimeError(err_msg)

                try:
                    async with httpx.AsyncClient(timeout=2.0) as client:
                        resp = await client.get(health_url)
                        if resp.status_code == 200:
                            is_ready = True
                            break
                except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
                    pass

                await asyncio.sleep(0.3)

            startup_dur_ms = round((time.time() - start_time) * 1000, 2)
            if not is_ready:
                # Startup timeout reached: terminate process
                self._terminate_process_sync(info)
                info.state = WorkerState.UNHEALTHY
                info.last_error = f"Worker '{model_name}' startup timed out after {self.startup_timeout}s."
                info.record_crash(time.time())
                log_tail = self._read_log_tail(info.log_file)
                try:
                    from app.core.metrics import metrics_collector
                    from app.core.observability_logger import emit_structured_log
                    metrics_collector.record_worker_startup(model_name, startup_dur_ms, success=False)
                    emit_structured_log(
                        "ERROR",
                        "WORKER_STARTUP_TIMEOUT",
                        f"Worker '{model_name}' startup timed out after {self.startup_timeout}s",
                        worker=model_name,
                        duration_ms=startup_dur_ms,
                    )
                except Exception:
                    pass
                raise RuntimeError(
                    f"Worker '{model_name}' failed to start within {self.startup_timeout} seconds.\n"
                    f"Logs:\n{log_tail}"
                )

            info.state = WorkerState.HEALTHY
            info.last_used_at = time.time()
            try:
                from app.core.metrics import metrics_collector
                from app.core.observability_logger import emit_structured_log
                metrics_collector.record_worker_startup(model_name, startup_dur_ms, success=True)
                emit_structured_log(
                    "INFO",
                    "WORKER_STARTUP",
                    f"Worker '{model_name}' started successfully in {startup_dur_ms:.2f}ms",
                    worker=model_name,
                    duration_ms=startup_dur_ms,
                    details={"pid": info.pid, "port": info.port},
                )
            except Exception:
                pass

    def _fire_crash_loop_alert(self, model_name: str, info: WorkerProcessInfo) -> None:
        try:
            from app.core.alert_manager import alert_manager, AlertSeverity
            alert_manager.fire(
                rule_name="worker_crash_loop",
                severity=AlertSeverity.CRITICAL,
                title=f"Worker Crash-Loop: {model_name}",
                description=f"Worker '{model_name}' triggered crash-loop limiter ({len(info.recent_crashes)} crashes in {RESTART_WINDOW_SECONDS}s). Cooldown active.",
                details={
                    "worker": model_name,
                    "port": info.port,
                    "backoff_seconds": CRASH_LOOP_BACKOFF_SECONDS,
                    "crash_count": len(info.recent_crashes),
                },
                fingerprint=f"worker_crash_loop:{model_name}",
            )
        except Exception:
            pass

    @asynccontextmanager
    async def lease(self, model_name: str):
        info = self.get_info(model_name)
        info.active_requests += 1
        info.last_used_at = time.time()
        try:
            yield info
        finally:
            info.active_requests = max(0, info.active_requests - 1)
            info.last_used_at = time.time()

    def _read_log_tail(self, log_path: Path, max_lines: int = 15) -> str:
        if not log_path.exists():
            return "(No log file found)"
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            return "".join(lines[-max_lines:]).strip()
        except Exception as exc:
            return f"(Could not read log file: {exc})"

    def _terminate_process_sync(self, info: WorkerProcessInfo) -> None:
        if info.process is None:
            return
        try:
            info.process.terminate()
            for _ in range(10):
                if info.process.poll() is not None:
                    break
                time.sleep(0.1)
            if info.process.poll() is None:
                info.process.kill()
                info.process.poll()
        except Exception:
            pass
        finally:
            info.process = None
            info.pid = None

    async def stop_worker(self, model_name: str, force: bool = False) -> bool:
        info = self.get_info(model_name)
        async with info.lock:
            if info.process is None or info.process.poll() is not None:
                info.process = None
                info.pid = None
                if not info.disabled and info.state != WorkerState.CRASH_LOOP_BACKOFF:
                    info.state = WorkerState.STOPPED
                return True

            if info.active_requests > 0 and not force:
                return False

            info.state = WorkerState.STOPPING
            proc = info.process

            try:
                proc.terminate()
                for _ in range(20):
                    if proc.poll() is not None:
                        break
                    await asyncio.sleep(0.15)

                if proc.poll() is None:
                    proc.kill()
                    proc.poll()
            except Exception:
                pass
            finally:
                info.process = None
                info.pid = None
                info.state = WorkerState.STOPPED

            return True

    async def check_idle_workers(self) -> None:
        now = time.time()
        for name, info in list(self._workers.items()):
            if info.disabled or info.state != WorkerState.HEALTHY or info.process is None:
                continue

            if info.active_requests > 0:
                continue

            last_used = info.last_used_at or info.started_at or now
            if now - last_used >= self.idle_timeout:
                stopped = await self.stop_worker(name, force=False)
                if stopped:
                    try:
                        from app.core.metrics import metrics_collector
                        from app.core.observability_logger import emit_structured_log
                        metrics_collector.record_worker_reap(name)
                        emit_structured_log(
                            "INFO",
                            "WORKER_IDLE_REAP",
                            f"Worker '{name}' stopped after {round(now - last_used, 1)}s idle",
                            worker=name,
                        )
                    except Exception:
                        pass

    async def _reaper_loop(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(REAPER_INTERVAL)
                await self.check_idle_workers()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def start_reaper_task(self) -> None:
        if self._reaper_task is None or self._reaper_task.done():
            self._is_running = True
            loop = asyncio.get_event_loop()
            self._reaper_task = loop.create_task(self._reaper_loop())

    def stop_reaper_task(self) -> None:
        self._is_running = False
        if self._reaper_task is not None and not self._reaper_task.done():
            self._reaper_task.cancel()

    async def stop_all_workers(self) -> None:
        self.stop_reaper_task()
        for name in list(self._workers.keys()):
            await self.stop_worker(name, force=True)

    def get_status(self) -> Dict[str, Any]:
        now = time.time()
        status_dict: Dict[str, Any] = {}
        try:
            from app.core.metrics import metrics_collector
            model_metrics = metrics_collector.model_metrics
        except Exception:
            model_metrics = {}

        for name, info in self._workers.items():
            stats = model_metrics.get(name, {})
            in_backoff = info.is_in_backoff(now)
            backoff_remaining = round(info.backoff_until - now, 1) if (in_backoff and info.backoff_until) else 0.0

            if info.disabled:
                status_dict[name] = {
                    "port": info.port,
                    "state": WorkerState.DISABLED.value,
                    "reason": info.disabled_reason or "model unavailable",
                    "pid": None,
                    "active_requests": 0,
                    "idle_seconds": None,
                    "startup_count": stats.get("startup_count", 0),
                    "crash_count": stats.get("crash_count", 0),
                    "reap_count": stats.get("reap_count", 0),
                    "in_crash_loop_backoff": False,
                    "backoff_remaining_seconds": 0.0,
                }
                continue

            # Update live process state if it exited unexpectedly
            if info.process is not None and info.process.poll() is not None:
                info.state = WorkerState.CRASHED
                info.pid = None
                info.process = None

            last_used = info.last_used_at or info.started_at
            idle_secs = round(now - last_used, 1) if (last_used and info.state == WorkerState.HEALTHY) else None

            status_dict[name] = {
                "port": info.port,
                "state": info.state.value,
                "pid": info.pid,
                "active_requests": info.active_requests,
                "idle_seconds": idle_secs,
                "idle_timeout": self.idle_timeout,
                "last_error": info.last_error,
                "startup_count": stats.get("startup_count", 0),
                "crash_count": stats.get("crash_count", 0),
                "reap_count": stats.get("reap_count", 0),
                "last_startup_duration_ms": stats.get("last_startup_duration_ms", 0.0),
                "in_crash_loop_backoff": in_backoff,
                "backoff_remaining_seconds": backoff_remaining,
                "recent_crash_count": len(info.recent_crashes),
            }

        return {"workers": status_dict}


worker_manager = WorkerLifecycleManager()
