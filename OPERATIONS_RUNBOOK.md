# FetalAI Production Operations Runbook

**Version**: 1.0  
**Target Environment**: Production (Render / Neon PostgreSQL)  
**Classification**: Internal Operations & Site Reliability Engineering (SRE)

---

## 1. System Topology & Operational Architecture

| Component | Host / Port | Runtime | Memory Target | Purpose |
|---|---|---|---|---|
| **Main API Gateway** | `0.0.0.0:8000` | Python 3.10 | < 150 MB (ML-Free) | Routing, Auth, IDOR, Metrics, Reports, Sessions |
| **Plane Worker** | `127.0.0.1:8100` | Python 3.10 | ~80 MB | Fetal standard plane classification |
| **Spine Worker** | `127.0.0.1:8101` | Python 3.10 | ~90 MB | Spine anomaly detection (YOLOv8) |
| **Brain Worker** | `127.0.0.1:8102` | Python 3.10 | ~90 MB | Transventricular brain analysis |
| **Lung Worker** | `127.0.0.1:8103` | Python 3.10 | ~90 MB | Four-chamber lung segmentation |
| **Bone Worker** | `127.0.0.1:8105` | Python 3.10 | ~90 MB | Femur bone biometric analysis |
| **Placenta Worker** | `127.0.0.1:8106` | Python 3.10 | ~90 MB | Placenta segmentation & localization |
| **Face Worker** | `127.0.0.1:8107` | Python 3.11 + VTK | ~120 MB | 3D facial feature volumetric analysis |
| **Heart Worker** | `127.0.0.1:8108` | Python 3.10 | ~90 MB | Cardiac view segmentation |
| **Kidney Worker** | `127.0.0.1:8109` | **DISABLED** | 0 MB | Guarded with `503 WORKER_DISABLED` |
| **Neon PostgreSQL** | Cloud Pooler:5432 | PostgreSQL 16 | External | Relational data, users, sessions, reports |

---

## 2. Real-Time Probes & Health Evaluation

| Endpoint | Method | Response Codes | Description |
|---|---|---|---|
| `/health` | `GET` | `200` | Gateway liveness, RSS memory posture, active alert count |
| `/health/readiness` | `GET` | `200` (Ready/Degraded), `503` (Unhealthy) | DB pre-ping, DB latency, worker pool status |
| `/health/workers` | `GET` | `200` | State, PID, port, crash counts, and backoff state of all 9 workers |
| `/health/alerts` | `GET` | `200` | Unified health status (`HEALTHY`, `DEGRADED`, `UNAVAILABLE`), active alerts |
| `/health/metrics` | `GET` | `200` | Bounded operational metrics (requests, latency, models, security counters) |

---

## 3. Standard Operational Incident Response Playbooks

---

### Incident 1: Database Connectivity Drop / Timeout
- **Symptoms**:
  - `/health/readiness` returns `HTTP 503` with `database: disconnected`.
  - Alert `database_connectivity` enters `CRITICAL` state.
  - API requests returning `500` or database timeout errors.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health/readiness
  curl -s http://127.0.0.1:8000/health/alerts
  ```
- **Immediate Action**:
  1. Inspect Neon Database dashboard for compute pause or maintenance window.
  2. Verify network egress from Gateway container to Neon endpoint on port 5432.
  3. Verify connection pool credentials in `.env` (`POSTGRES_HOST`, `POSTGRES_PASSWORD`).
  4. Database pool has `pool_pre_ping=True` enabled; once connectivity resumes, `/health/readiness` automatically returns to `200` and alert auto-resolves.
- **Recovery Verification**:
  ```bash
  curl -s http://127.0.0.1:8000/health/readiness | grep '"database":"connected"'
  ```

---

### Incident 2: ML Worker Process Crash-Loop
- **Symptoms**:
  - Alert `worker_crash_loop:{worker}` fires with severity `CRITICAL`.
  - Worker state transitions to `crash_loop_backoff`.
  - Inference requests for that worker return `503` with cooldown notice.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health/workers
  tail -n 30 backend/storage/worker_logs/{worker}_worker.log
  ```
- **Immediate Action**:
  1. Inspect the worker log file `backend/storage/worker_logs/{worker}_worker.log` for model loading failures (missing weights, corrupt checkpoint, or CUDA/CPU mismatch).
  2. For `face` worker, ensure Python 3.11 environment with VTK 9.7.0 is active.
  3. Backoff cooldown lasts 30 seconds to prevent CPU/memory thrashing.
  4. Fix weights file in `backend/app/ml/models/` if corrupted.
  5. Trigger manual restart via standard inference request once cooldown expires.
- **Recovery Verification**:
  ```bash
  curl -s http://127.0.0.1:8000/health/workers | grep '"state":"healthy"'
  ```

---

### Incident 3: Gateway High Memory Pressure (>400 MB RSS)
- **Symptoms**:
  - `/health` indicates `high_memory_warning: true`.
  - Alert `high_memory_pressure` fires with severity `WARNING`.
  - Health evaluation reports `overall_status: DEGRADED`.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health
  curl -s http://127.0.0.1:8000/health/metrics | grep memory
  ```
- **Immediate Action**:
  1. Verify Gateway process memory: Gateway MUST be ML-free (< 150 MB typical).
  2. If memory > 400 MB, check if child worker reaping is lagging (`/health/workers`).
  3. Force idle worker cleanup: idle reaper stops workers idle >= 300s.
  4. If process leak detected in third-party library, restart Gateway container.
- **Recovery Verification**:
  ```bash
  curl -s http://127.0.0.1:8000/health | grep '"high_memory_warning":false'
  ```

---

### Incident 4: Slow Request Spike / Latency Degradation (>2000ms)
- **Symptoms**:
  - Structured logs show `SLOW_REQUEST` warnings.
  - `/health/metrics` shows rising `slow_requests_count`.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health/metrics | grep -A 10 recent_slow_requests
  ```
- **Immediate Action**:
  1. Inspect `recent_slow_requests` deque in `/health/metrics` to identify offending endpoints.
  2. If slow endpoint is `/api/v1/inference/comprehensive`, check which worker model has high latency in `models` metrics.
  3. If slow endpoint is database-related, check Neon DB query performance and connection pool wait time (`DB_POOL_TIMEOUT=30`).
- **Recovery Verification**:
  Verify subsequent request durations drop below 2000ms.

---

### Incident 5: Authentication Storm / JWT Verification Failures
- **Symptoms**:
  - Security logs show elevated `AUTH_LOGIN_FAILURE` or `JWT_INVALID`.
  - Security counter in `/health/metrics` increments rapidly.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health/metrics | grep -A 10 security
  ```
- **Immediate Action**:
  1. Check client IP addresses triggering login failures.
  2. Rate limiter automatically blocks IPs exceeding 10 attempts/minute on `/api/auth/login`.
  3. If valid users report token expiry, check clock drift or token lifetime setting (`ACCESS_TOKEN_EXPIRE_MINUTES`).

---

### Incident 6: Rate Limiting Storm / DoS Attack
- **Symptoms**:
  - Client receives `HTTP 429 Rate limit exceeded`.
  - Security metric `rate_limit_exceeded` spikes.
- **Verification Commands**:
  ```bash
  curl -s http://127.0.0.1:8000/health/metrics | grep rate_limit_exceeded
  ```
- **Immediate Action**:
  1. Rate limiter operates on in-memory sliding windows (Auth: 10/min, Inference: 20/min, Uploads: 30/min, General: 120/min).
  2. Legitimate automated tests or clients must back off according to the `Retry-After` header.
  3. In extreme volumetric attacks, block malicious IP ranges at cloud reverse proxy / CDN level.

---

### Incident 7: Malformed / Malicious Upload Exploitation Attempt
- **Symptoms**:
  - Security audit logs show `UPLOAD_INVALID_EXT`, `UPLOAD_MALFORMED`, or `PATH_TRAVERSAL_BLOCKED`.
- **Immediate Action**:
  1. FetalAI sanitizes all uploaded filenames via `sanitize_filename()` (strips path separators, directory traversal tokens `../`, and normalizes to UUID prefixes).
  2. Supported extensions: `.png`, `.jpg`, `.jpeg`, `.dcm`. Executable files (`.exe`, `.sh`, `.py`) are rejected with `HTTP 400`.
  3. No administrative action needed; upload sanitizer neutralizes malicious payloads automatically.

---

### Incident 8: Analysis Session Interruption & Stale State Recovery
- **Symptoms**:
  - Gateway crashed or restarted during long-running multi-model inference.
  - Sessions left in `processing` state in database.
- **Verification & Resolution**:
  1. On Gateway startup, `session_service.recover_stale_sessions()` automatically scans for sessions stuck in `processing` and marks them as `interrupted`.
  2. Clinicians can click **Retry** in UI or POST `/api/v1/analysis/sessions/{session_id}/retry` to transition status from `interrupted` back to `ready`.
  3. Metric `stale_sessions_recovered` tracks recovery operations.

---

### Incident 9: Comprehensive Analysis Partial Worker Outage
- **Symptoms**:
  - Comprehensive analysis completes with `status: "partial"`.
  - Some models succeed while one worker timed out or is disabled (e.g. Kidney).
- **Behavior & Resolution**:
  1. The pipeline is designed to be fully failure-tolerant: individual model failures do NOT abort the entire scan analysis.
  2. Missing findings are documented in Section 11 / 14 of the clinical report.
  3. Clinician can re-run missing models once the worker is restored.

---

### Incident 10: Report / PDF Generation Failure & Stream Interruption
- **Symptoms**:
  - Metric `pdf_stream_failures` increments.
  - User cannot download PDF report.
- **Verification & Resolution**:
  1. Verify ReportLab is installed in Gateway environment (`pip show reportlab`).
  2. Check report metadata in DB: report snapshot JSON is immutable and stored permanently.
  3. PDF is generated on demand from the immutable snapshot. Re-trigger download from `/api/v1/reports/{report_id}/pdf`.

---

### Incident 11: Worker Port Conflict / Zombie Subprocess Cleanup
- **Symptoms**:
  - Worker fails to bind port on startup (`Address already in use`).
- **Immediate Action**:
  ```powershell
  # Windows: find PID bound to port (e.g., 8100)
  netstat -ano | findstr :8100
  taskkill /F /PID <PID>
  ```
  ```bash
  # Linux: find PID bound to port
  lsof -i :8100
  kill -9 <PID>
  ```
  Gateway graceful shutdown hook (`stop_all_workers`) terminates all child worker processes cleanly.

---

### Incident 12: Zero-Downtime Rolling Update & Health Verification
- **Deployment Procedure**:
  1. Deploy new container image.
  2. Platform routes traffic to new container only after `/health/readiness` returns `HTTP 200` with `status: ready`.
  3. On startup, new container recovers stale sessions and starts background reaper task.
  4. Terminate old container gracefully (allows 30s for active HTTP requests to drain).

---

## 4. Automated Maintenance & Disaster Recovery Operations

### A. Automated Daily Maintenance Suite
Run the scheduled maintenance suite for automated backup, retention pruning, and probe health audit:
```bash
py -3.10 "scratch/automated_maintenance_suite.py"
```

### B. Disaster Recovery Execution (RTO < 15m)
1. **Database Restoration Drill**:
   ```bash
   py -3.10 "scratch/run_recovery_drill.py"
   ```
2. **Storage Volume Restoration Drill**:
   ```bash
   py -3.10 "scratch/test_storage_disaster_recovery.py"
   ```
3. Full verification protocols are detailed in [`POST_RECOVERY_DRILL_REPORT.md`](./POST_RECOVERY_DRILL_REPORT.md) and [`MAINTENANCE_CHECKLIST.md`](./MAINTENANCE_CHECKLIST.md).

