# FetalAI Production Monitoring & Observability Guide

## 1. Overview & Architecture

FetalAI v1.0 features a lightweight, zero-dependency, in-memory monitoring and observability engine designed for low-memory cloud deployments (~512 MB RAM).

```
+-----------------------------------------------------------------------------------+
|                           CLIENT / MONITORING PROBES                              |
+------------------------------------------+----------------------------------------+
                                           | HTTP (X-Request-ID Header)
                                           v
+-----------------------------------------------------------------------------------+
|                    FASTAPI GATEWAY & API ORCHESTRATOR (Port 8000)                 |
|                                [STRICTLY ML-FREE]                                 |
|                                                                                   |
|  - MetricsCollector (Thread-Safe, Bounded)  - Structured JSON Observability Logger|
|  - Request Latency & Status Distribution   - Memory / RSS Pressure Monitoring    |
|  - Slow Request Detection (Configurable)   - Database Ping Latency Tracking      |
|  - Worker Lifecycle Event Tracking         - Security Audit Counters & Redaction |
+----+--------+--------+--------+--------+--------+--------+--------+---------------+
     |        |        |        |        |        |        |        | (Disabled)
     v :8100  v :8101  v :8102  v :8103  v :8105  v :8106  v :8107  v :8108  v :8109
  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+
  |Plane|  |Spine|  |Brain|  |Lung |  |Bone |  |Plac.|  |Face |  |Heart|  |Kidn.|
  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+  +-----+
```

---

## 2. Health & Observability Endpoints

| Endpoint | Method | Purpose | Response Characteristics |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | **Liveness Probe**: Confirms API Gateway process vitality and memory posture. | `200 OK` with uptime, RSS memory (MB), and high-memory warning flag. |
| `/health/readiness` | `GET` | **Readiness Probe**: Tests live PostgreSQL database connection via `SELECT 1` without loading ML models. | `200 OK` (ready) or `503 Service Unavailable` with DB ping latency. |
| `/health/workers` | `GET` | **Worker Status Probe**: Queries child worker lifecycle states, PIDs, and active leases passively. | `200 OK` with detailed worker states (Kidney strictly reported as `disabled`). |
| `/health/metrics` | `GET` | **Operational Metrics Endpoint**: Returns real-time aggregate performance, latency, and session stats. | `200 OK` with sanitized metrics JSON (zero secrets, zero patient PII). |

---

## 3. Metrics Structure (`GET /health/metrics`)

The metrics endpoint returns a comprehensive JSON object:

```json
{
  "timestamp": "2026-09-06T02:40:00.000Z",
  "service": "fetalai-gateway",
  "uptime_seconds": 3600.0,
  "memory": {
    "rss_bytes": 96123456,
    "rss_mb": 91.67,
    "high_memory_threshold_mb": 400.0,
    "is_high_memory_pressure": false,
    "uptime_seconds": 3600.0
  },
  "requests": {
    "total": 1250,
    "successful": 1200,
    "failed": 50,
    "status_distribution": {
      "200": 1150,
      "201": 50,
      "400": 20,
      "401": 15,
      "404": 10,
      "429": 3,
      "503": 2
    },
    "slow_requests_count": 5,
    "slow_threshold_ms": 2000.0,
    "recent_slow_requests": [
      {
        "timestamp": "2026-09-06T02:35:10.000Z",
        "request_id": "req_abc123456789",
        "method": "POST",
        "path": "/api/v1/inference/comprehensive",
        "status_code": 200,
        "duration_ms": 9469.11
      }
    ],
    "top_endpoints": {
      "POST /api/v1/inference/comprehensive": {
        "count": 45,
        "total_ms": 405000.0,
        "min_ms": 7500.0,
        "max_ms": 14200.0,
        "avg_ms": 9000.0,
        "errors": 0
      }
    }
  },
  "models": {
    "plane": {
      "disabled": false,
      "requests": 150,
      "success": 150,
      "failures": 0,
      "timeouts": 0,
      "avg_latency_ms": 45.2,
      "max_latency_ms": 120.5,
      "startup_count": 1,
      "restart_count": 0,
      "crash_count": 0,
      "reap_count": 0,
      "last_startup_duration_ms": 120.5,
      "last_used_at": "2026-09-06T02:38:00.000Z"
    },
    "kidney": {
      "disabled": true,
      "requests": 0,
      "success": 0,
      "failures": 0,
      "timeouts": 0
    }
  },
  "comprehensive_pipeline": {
    "total_runs": 45,
    "completed": 45,
    "partial": 0,
    "failed": 0,
    "avg_duration_ms": 9000.0,
    "max_duration_ms": 14200.0
  },
  "sessions": {
    "state_transitions": {
      "ready": 45,
      "processing": 45,
      "completed": 45,
      "interrupted": 0
    },
    "idempotent_cache_hits": 12,
    "stale_sessions_recovered": 0
  },
  "reports": {
    "reports_generated": 45,
    "avg_report_duration_ms": 0.0,
    "pdf_generated": 30,
    "avg_pdf_duration_ms": 65.0,
    "pdf_stream_failures": 0,
    "report_lookup_failures": 0,
    "report_authz_denials": 0
  },
  "database": {
    "total_pings": 120,
    "successful_pings": 120,
    "failed_pings": 0,
    "last_ping_latency_ms": 1058.57,
    "last_ping_status": "connected",
    "last_ping_timestamp": "2026-09-06T02:39:50.000Z"
  },
  "security": {
    "auth_login_success": 25,
    "auth_login_failure": 2,
    "authz_denied": 5,
    "jwt_invalid": 1,
    "jwt_expired": 1,
    "rate_limit_exceeded": 3,
    "upload_invalid_ext": 1,
    "upload_malformed": 1,
    "path_traversal_blocked": 1
  }
}
```

---

## 4. Structured Machine-Readable JSON Logging

All key events emit structured JSON to stdout/log streams.

### Log Format
```json
{
  "timestamp": "2026-09-06T02:35:10.000Z",
  "level": "INFO | WARN | ERROR",
  "service": "backend",
  "event_type": "HTTP_REQUEST | SLOW_REQUEST | INFERENCE_SUCCESS | WORKER_STARTUP | REPORT_GENERATED | ...",
  "message": "Human-readable description",
  "request_id": "req_abc123456789",
  "endpoint": "POST /api/v1/inference/comprehensive",
  "status_code": 200,
  "duration_ms": 9469.11,
  "worker": "plane",
  "model": "fetal_plane_classifier",
  "details": {}
}
```

### Key Event Types
- `SLOW_REQUEST`: Emitted when request latency exceeds `SLOW_REQUEST_THRESHOLD_MS` (default 2000ms).
- `WORKER_STARTUP`: Emitted on successful worker process spawn and health verification.
- `WORKER_CRASH`: Emitted if a child worker process terminates prematurely.
- `WORKER_IDLE_REAP`: Emitted when an idle worker is stopped after exceeding the idle timeout (default 300s).
- `INFERENCE_SUCCESS` / `INFERENCE_TIMEOUT` / `INFERENCE_ERROR`: Worker inference performance events.
- `COMPREHENSIVE_ANALYSIS`: Multi-model pipeline completion.
- `REPORT_GENERATED` / `PDF_GENERATION`: Clinical report snapshot and ReportLab PDF streaming events.
- `SECURITY_AUDIT`: Authentication and authorization events (`AUTHZ_DENIED`, `AUTH_LOGIN_FAILURE`).

---

## 5. Security & Sensitive Data Redaction

FetalAI strictly guarantees that no sensitive credentials or personal identifiable information (PII) are recorded in monitoring logs or metrics:
1. **Passwords & Tokens**: Automatically redacted (`"[REDACTED]"`).
2. **JWT Secret Keys & API Keys**: Filtered from all log dictionaries.
3. **Binary Payloads**: Logged only as `<N bytes binary payload>`.
4. **Error Payloads**: Normalized to standard error codes without leaking internal server filesystem paths or raw stack traces.

---

## 6. Configuration Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `SLOW_REQUEST_THRESHOLD_MS` | `2000` | Latency threshold (ms) above which requests are logged as `SLOW_REQUEST`. |
| `HIGH_MEMORY_THRESHOLD_MB` | `400.0` | Gateway RSS threshold (MB) that activates `is_high_memory_pressure` warning flag. |
| `METRICS_ENABLED` | `true` | Enables in-memory operational metrics collection. |
| `WORKER_IDLE_TIMEOUT_SECONDS` | `300` | Duration (seconds) of inactivity before idle workers are gracefully terminated. |
| `WORKER_STARTUP_TIMEOUT_SECONDS` | `60` | Maximum duration (seconds) to wait for a worker to start and respond to `/health`. |

---

## 7. Troubleshooting & Operational Guide

### Scenario 1: Readiness Probe Fails (`503 Service Unavailable`)
1. Inspect `/health/readiness` output: check if `database: disconnected`.
2. Inspect database connectivity and network latency to PostgreSQL Neon DB.
3. Verify `DATABASE_URL` credentials in `.env`.

### Scenario 2: High Memory Warning Triggered (`is_high_memory_pressure = true`)
1. Query `/health/metrics` to inspect `memory.rss_mb`.
2. Check `/health/workers` to see how many worker processes are currently spawned.
3. Idle workers will automatically be reaped by the background reaper task after 300 seconds of inactivity.
4. If immediate reclamation is needed, call `POST /api/v1/inference/workers/{model_name}/stop`.

### Scenario 3: Inference Timeout (`504 Gateway Timeout`)
1. Check `/health/metrics` -> `models.{model_name}.timeouts`.
2. Review logs for `INFERENCE_TIMEOUT`.
3. Verify GPU/CPU resource allocation on the worker host.
