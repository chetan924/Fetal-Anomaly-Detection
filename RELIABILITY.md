# FetalAI Architectural Reliability & System Resilience

**Version**: 1.0  
**Target Platform**: FetalAI Clinical Prototype API  
**Classification**: Architectural Design & Reliability Engineering

---

## 1. Reliability Principles & Failure Domain Isolation

FetalAI achieves production-grade stability on constrained infrastructure (~512 MB RAM environments) through three core architectural tenets:

```
+-------------------------------------------------------------------------+
|                         CLIENT APPLICATIONS                             |
|             (React Web UI / Mobile / Clinical Integrations)             |
+-------------------------------------------------------------------------+
                                    |
                                    | (HTTPS / Rate Limited / Monitored)
                                    v
+-------------------------------------------------------------------------+
|                  MAIN API GATEWAY (Port 8000)                           |
|  - 100% ML-Free (< 150 MB RSS)                                         |
|  - Fast routing, JWT Auth, IDOR Defense, Session Service, ReportLab     |
|  - Thread-Safe Metrics & Provider-Neutral AlertManager                  |
+-------------------------------------------------------------------------+
       |             |             |             |             |
  (Port 8100)   (Port 8101)   (Port 8102)   (Port 8103)   (Port 8105..8108)
       v             v             v             v             v
  +----------+  +----------+  +----------+  +----------+  +---------------+
  |  Plane   |  |  Spine   |  |  Brain   |  |   Lung   |  | Face, Placenta|
  |  Worker  |  |  Worker  |  |  Worker  |  |  Worker  |  | Heart Workers |
  +----------+  +----------+  +----------+  +----------+  +---------------+
       |             |             |             |             |
       +-------------+-------------+-------------+-------------+
                                   |
                  (On-Demand Spawn & 300s Idle Reaping)
```

### A. Strict Process Separation (ML-Free Gateway)
- Heavy deep learning frameworks (`torch`, `torchvision`, `ultralytics`, `vtk`, `cv2`) are completely absent from the Gateway process.
- Gateway memory remains bounded at ~90-120 MB RSS, insulating the primary API from ML memory spikes, CUDA allocations, or library segmentation faults.

### B. Worker Crash-Loop Protection & Thrashing Mitigation
- Child ML workers operate with an automatic sliding-window restart limiter:
  - **Threshold**: Maximum 3 restarts within 60 seconds (`MAX_RESTART_ATTEMPTS = 3`, `RESTART_WINDOW_SECONDS = 60.0`).
  - **Backoff**: If a worker exceeds the threshold, it is placed in `WorkerState.CRASH_LOOP_BACKOFF` for 30 seconds.
  - **Protection**: Rapid restarts that would starve Gateway CPU or trigger Out-Of-Memory (OOM) kernel kills are prevented.
  - **Alerting**: Emits `CRITICAL` alert `worker_crash_loop:{worker}` and records crash counters in metrics.

### C. Graceful Degradation in Multi-Model Analysis
- The Comprehensive Analysis pipeline executes across up to 8 independent workers concurrently.
- If an individual worker fails or is disabled (e.g. Kidney worker at port 8109), the pipeline gracefully continues and completes with status `partial`.
- The final clinical report captures available findings while explicitly documenting unanalyzed structures in Section 11 and Section 14.

---

## 2. Service Health State Model

FetalAI provides a 3-tier unified operational health status:

| Health State | Conditions | Gateway HTTP Status | Action Required |
|---|---|---|---|
| **`HEALTHY`** | Gateway alive, DB connected (< 5s latency), zero critical alerts, zero crash loops, memory normal | `200 OK` | None (nominal operation) |
| **`DEGRADED`** | Gateway & DB alive, but memory pressure high (> 400 MB), slow request burst, or non-critical worker issue | `200 OK` | Monitor metrics; check idle reaper or model latency |
| **`UNAVAILABLE`** | Database disconnected or unrecoverable system dependency failure | `503 Service Unavailable` | SRE intervention required; check DB connectivity |

---

## 3. Session State Resilience & Idempotency

### A. Idempotent Ingestion & Deduplication
- Clinical inference requests accept an optional `Idempotency-Key` header (or UUID).
- Duplicate submissions within 24 hours immediately return the previously computed immutable report snapshot without re-running heavy ML pipelines (`is_cached: true`).

### B. Gateway Crash Recovery & Stale Session Reconciliation
- On Gateway startup, `session_service.recover_stale_sessions()` automatically scans the database for any sessions abandoned in `processing` state due to container restart.
- These sessions transition safely to `interrupted`.
- Clinicians can trigger `/api/v1/analysis/sessions/{id}/retry` to re-enqueue and process the session without data corruption.

---

## 4. Immutable Report Architecture

- All clinical report findings are serialized into frozen JSON snapshots upon initial creation.
- PDF downloads render deterministically from the stored snapshot using ReportLab.
- Subsequent updates to ML models or worker code will never alter historical clinical records, guaranteeing complete audit compliance and reproducibility.

---

## 5. Service Level Objectives (SLOs)

| Metric | Target | Measurement Window |
|---|---|---|
| **API Availability** | **>= 99.9%** | Rolling 30 Days |
| **P95 Gateway Route Latency** | **< 250 ms** | Standard CRUD / Auth endpoints |
| **P95 Single Model Inference** | **< 2.5 s** | Individual ML worker execution |
| **P95 Comprehensive Pipeline** | **< 15.0 s** | Full 8-model parallel execution |
| **Database Ping Latency** | **< 100 ms** | Connection pool pre-ping |
| **Peak Gateway Memory** | **< 250 MB** | 100 concurrent requests |
