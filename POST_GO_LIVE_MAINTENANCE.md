# FetalAI v1.0 — Post-Go-Live Operational Maintenance Guide

**Project**: FetalAI Clinical AI Ultrasound Platform  
**Target Root**: `D:\Fetal Anomaly Detection`  
**Version**: `v1.0.0` (Release Frozen & Production Validated)  
**Maintenance Posture**: Zero-Cost In-Memory Observability & Operational Runbooks  

---

## 1. Operational Maintenance Schedules

All maintenance tasks are strictly classified by their operational nature:
- `[AUTOMATED]` — Continuously executed by Gateway background tasks, database drivers, or middleware.
- `[MANUAL]` — Routine administrator or clinical IT inspections.
- `[UNVERIFIED]` — Procedures defined and verified dry-run, but not destructively executed against active production data.

### 1.1 Daily Maintenance Checklist
| Frequency | Task | Operational Category | Verification Method |
|---|---|---|---|
| Daily | Probe Gateway Liveness (`/health`) | `[AUTOMATED]` / `[MANUAL]` | HTTP GET `http://localhost:8000/health` (Expect: 200 OK) |
| Daily | Database Ping & Latency Check (`/health/readiness`) | `[AUTOMATED]` / `[MANUAL]` | HTTP GET `http://localhost:8000/health/readiness` (Expect: 200 OK, latency < 100ms) |
| Daily | Worker Fleet Status (`/health/workers`) | `[AUTOMATED]` | Background Reaper + HTTP GET `/health/workers` |
| Daily | Firing Alerts Review (`/health/alerts?active_only=true`) | `[AUTOMATED]` | Alert Manager deduplicated cache |
| Daily | In-Memory Metrics Review (`/health/metrics`) | `[AUTOMATED]` | Metrics Collector summary |

### 1.2 Weekly Maintenance Checklist
| Frequency | Task | Operational Category | Verification Method |
|---|---|---|---|
| Weekly | Verify Rate Limiting Counter Resets & Status | `[AUTOMATED]` | Rate Limiter sliding window expiry verification |
| Weekly | Inspect `storage/worker_logs/` Disk Footprint | `[MANUAL]` | Check directory size; remove stale transient worker stderr logs |
| Weekly | Audit Security Logs for `AUTHZ_DENIED` Spike | `[MANUAL]` | Filter structured logs for `AUTHZ_DENIED` and `IDOR` patterns |
| Weekly | Validate Stale Session Recovery Pipeline | `[AUTOMATED]` | Startup hook / background session recovery audit |
| Weekly | Verify Neon PostgreSQL Connection Pool Metrics | `[AUTOMATED]` | Check pool status (Pool size: 5, Max overflow: 10, Pre-ping: True) |

### 1.3 Monthly Maintenance Checklist
| Frequency | Task | Operational Category | Verification Method |
|---|---|---|---|
| Monthly | Review Configuration Drift against `.env.example` | `[MANUAL]` | Audit environment variables for drift or unrotated secrets |
| Monthly | Test Database Logical Backup Export (`pg_dump`) | `[MANUAL]` | Run zero-cost logical schema/data dump to offline encrypted storage |
| Monthly | Database Restoration Drill Verification | `[UNVERIFIED]` | Target staging environment; do not overwrite live production DB |
| Monthly | Static Code Architecture Invariant Audit | `[MANUAL]` | Run AST inspector ensuring zero ML libraries loaded in Gateway |
| Monthly | Frontend Production Build Hash Verification | `[MANUAL]` | Verify Vite static bundle integrity in `frontend/dist/` |

---

## 2. Zero-Cost Monitoring & Health Check Procedures

FetalAI v1.0 implements a **₹0 operational cost** monitoring and observability architecture. No external paid telemetry or SaaS tools are used. All metrics, health states, and alerts reside in-process with strict memory bounds.

### 2.1 Health Probe Endpoints
1. **Liveness Probe**: `GET /health`
   - Returns Gateway process vitality, uptime, process RSS memory (MB), and unified status.
   - Status: `ok` (healthy) or `degraded`.
2. **Readiness Probe**: `GET /health/readiness`
   - Performs active `SELECT 1` pre-ping across Neon PostgreSQL connection pool.
   - Returns DB status, latency (ms), and pool statistics.
3. **Worker Fleet Probe**: `GET /health/workers`
   - Returns health state, process PID, crash counts, and idle timestamps across all 10 worker slots (:8100-:8109).
4. **Metrics Endpoint**: `GET /health/metrics`
   - Exposes comprehensive in-memory counters across 11 categories: HTTP requests, slow requests, error rates, worker latency percentiles (p50/p95/p99), memory usage, and report volumes.
5. **Alerts Endpoint**: `GET /health/alerts`
   - Exposes active firing alerts, history, severity breakdown (`INFO`, `WARNING`, `CRITICAL`), deduplication fingerprints, and cooldown state.

---

## 3. Worker Lifecycle & Isolation Runbook

### 3.1 Worker Port Bindings Invariant
All ML inference is isolated into dedicated subprocesses listening on deterministic localhost ports:
- `:8100` — Fetal Plane Detection (YOLOv8 + ResNet50)
- `:8101` — Fetal Spine Analysis (ResNet50)
- `:8102` — Fetal Brain Anomaly (Multi-Head DenseNet)
- `:8103` — Fetal Lung Biometry (U-Net Segmentation)
- `:8104` — Fetal Abdomen Assessment (Reserved)
- `:8105` — Fetal Femur / Bone Biometry (ResNet50)
- `:8106` — Placental Location & Maturity (MobileNetV3)
- `:8107` — Fetal Face 3D Mesh (VTK PolyData / PyVista)
- `:8108` — Fetal Cardiac 4-Chamber Axis (Custom ResNet)
- `:8109` — Fetal Kidney Worker (**STRICTLY DISABLED — Policy Enforced 503**)

### 3.2 Dynamic Lifecycle & Reaper
- **On-Demand Spawning**: Workers are spawned as detached subprocesses upon first request.
- **Idle Worker Reaper**: Background task runs every 60 seconds. Workers idle for >10 minutes (`IDLE_TIMEOUT = 600s`) are gracefully terminated to reclaim RAM.
- **Crash-Loop Protection**: If a worker crashes 3 times consecutively, it enters exponential backoff (`crash_loop_backoff`), preventing CPU thrashing and triggering a `CRITICAL` alert.

### 3.3 Platform-Specific Isolation Constraints
- **Face Worker (VTK PolyData)**: On Windows hosts with strict AppLocker/WDAC DLL execution policies, VTK native C++ `.pyd` dynamic loading may encounter local OS blocks. The Gateway isolates this constraint gracefully, returning standard HTTP 503 envelopes (`WORKER_STARTUP_FAILED`) while preserving full Gateway uptime and other organ inferences. On standard Linux/Docker deployments, VTK loads natively.

---

## 4. Data Retention, Storage, and Log Rotation

### 4.1 Storage Layout
- `storage/scans/` — **Persistent**: Original uploaded ultrasound scan images (JPG, PNG, WEBP). File paths are sanitized UUIDs.
- `storage/explainability/` — **Persistent**: Generated Grad-CAM heatmaps, overlays, and visualization masks.
- `storage/worker_logs/` — **Transient**: Standard error and stdout streams from worker subprocesses. Safe for periodic cleanup.

### 4.2 Storage Maintenance Procedure
```powershell
# Check storage volume usage
Get-ChildItem -Path "backend\storage" -Recurse | Measure-Object -Property Length -Sum

# Routine cleanup of transient worker logs (>7 days old)
Get-ChildItem -Path "backend\storage\worker_logs" -Filter "*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } | Remove-Item -Force
```

---

## 5. Security Auditing & Access Control

### 5.1 Authentication & Authorization Safeguards
- **JWT Lifespan**: Access tokens expire strictly in 30 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES = 30`).
- **Cryptographic Signing**: HS256 algorithm with high-entropy secret key.
- **Strict IDOR Isolation**: Every resource fetch (`/api/patients/{id}`, `/api/scans/{id}`, `/api/v1/analysis/sessions/{id}`, `/api/v1/reports/{report_number}`, `/api/v1/reports/{report_number}/pdf`) requires matching `created_by == current_user.id` or `uploaded_by == current_user.id`. Cross-user access returns strict HTTP 404 (preventing user enumeration) and emits a `SECURITY_AUDIT: AUTHZ_DENIED` event.

### 5.2 Rate Limiting Policies
- **General Endpoints**: 60 requests/minute per client IP.
- **Inference Endpoints**: 10 requests/minute per client IP.
- **Authentication Endpoints**: 5 requests/minute per client IP.

---

## 6. Backup & Disaster Recovery Procedures

### 6.1 Point-in-Time Recovery (PITR)
Neon Serverless PostgreSQL maintains continuous write-ahead logging (WAL) and automated point-in-time recovery. Restorations can be initiated directly via Neon Console or Neon CLI.

### 6.2 Logical Backup Export (`pg_dump`)
```bash
pg_dump "postgresql://neondb_owner:***@ep-jolly-brook-aybehc6i-pooler.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  -F c -b -v -f "fetalai_backup_$(date +%Y%m%d_%H%M%S).dump"
```

### 6.3 Restoration Drill Verification Note
> [!IMPORTANT]
> **Status**: `RESTORE DRILL = UNVERIFIED` on Active Production Instance.  
> Logical restoration drills must only be executed against isolated staging or local database instances to avoid destructive overwrites of live clinical records.

---

## 7. Incident Response Triage Matrix

| Incident Severity | Root Cause | Symptoms | Immediate Triage Action |
|---|---|---|---|
| **Level 1 (Low)** | Worker idle or single crash | Temporary inference delay (<3s) on organ route | Worker Manager auto-restarts worker on next request. No manual action needed. |
| **Level 2 (Medium)** | Worker Crash-Loop | 503 `WORKER_STARTUP_FAILED`, alert firing | Check `storage/worker_logs/<worker>.log` for missing dependencies, GPU OOM, or permission blocks. |
| **Level 3 (High)** | PostgreSQL Disconnection | 500 / 503 on DB routes, alert `database_connectivity` | Check Neon console status, DNS resolution, and verify SSL connection strings in `.env`. |
| **Level 4 (Critical)** | Suspected IDOR / Brute-force | Spike in `AUTHZ_DENIED` logs, 429 rate limit triggers | Review audit logs for attacker IP, enforce firewall/WAF blocks if necessary. |

---

*FetalAI v1.0 Production Operations & Maintenance Runbook — Finalized & Validated.*

