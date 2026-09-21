# FetalAI v1.0 — Production Maintenance Checklist & Operations Runbook

**Version**: 1.0  
**Classification**: Production Operations & Site Reliability  
**Target Environment**: Neon PostgreSQL + Local/Mounted Storage Volumes  

---

## 1. Daily Operations Checklist (Automated / Manual)

### Daily Health Verification
- [ ] **Gateway Liveness**: Verify `GET /health` returns `200 OK` (`status: "ok"`).
- [ ] **Database Readiness**: Verify `GET /health/readiness` returns `200 OK` with `database_latency_ms < 2000ms`.
- [ ] **Worker Fleet Status**: Verify `GET /health/workers` reports 9 operational workers and 1 disabled worker (`kidney`).
- [ ] **Active Alerts**: Verify `GET /health/alerts` has 0 critical alerts firing.

### Daily Backup Execution (02:00 UTC)
- [ ] **PostgreSQL Snapshot**: Run automated logical database backup.
  ```bash
  py -3.10 "scratch/automated_maintenance_suite.py"
  ```
- [ ] **Storage Backup**: Verify `backend/storage/` snapshot is archived with valid SHA-256 checksum.
- [ ] **Backup Freshness Check**: Verify latest backup timestamp is $< 24\text{ hours}$ old and size $> 0\text{ bytes}$.

---

## 2. Weekly Maintenance Checklist

- [ ] **Storage Growth Audit**: Inspect disk usage in `backend/storage/scans/` and `backend/storage/explainability/`.
- [ ] **Log Rotation**: Inspect and archive worker diagnostic logs in `backend/storage/worker_logs/`.
- [ ] **Retention Pruning**: Prune backups older than the 30-day retention SLA.
- [ ] **Error Metric Review**: Query `GET /health/metrics` and ensure API error rates remain $< 0.1\%$.

---

## 3. Monthly Disaster Recovery Drills

- [ ] **Isolated Database Restore Drill**:
  - Run the non-destructive isolated schema restore script:
    ```bash
    py -3.10 "scratch/run_recovery_drill.py"
    ```
  - Confirm 100% row match across all 7 core tables and RTO $< 15\text{ minutes}$.
- [ ] **Isolated Storage Recovery Drill**:
  - Run the storage disaster recovery verification script:
    ```bash
    py -3.10 "scratch/test_storage_disaster_recovery.py"
    ```
  - Confirm 100% SHA-256 manifest match across all storage files.
- [ ] **Audit Findings**: Document all empirical measurements in `POST_RECOVERY_DRILL_REPORT.md`.

---

## 4. Quarterly Security & Dependency Audit

- [ ] **Python Package Audit**: Check installed backend packages for security advisories:
  ```bash
  pip list
  ```
- [ ] **Frontend NPM Security Audit**:
  ```bash
  cd frontend && npm audit
  ```
- [ ] **IDOR Protection Verification**: Run authorization regression tests to verify strict cross-user isolation:
  ```bash
  py -3.10 "scratch/test_security_hardening.py"
  ```

---

## 5. Incident Response Triage Protocol

### Scenario A: Database Connection Interruption
1. Check Neon PostgreSQL status dashboard.
2. Query `/health/readiness` to inspect database error details.
3. If pool connections are exhausted, restart the Gateway process; existing in-flight sessions will automatically transition to `interrupted` upon startup.

### Scenario B: Worker Crash or Crash-Loop Backoff
1. Query `/health/workers` to identify the failing worker.
2. The built-in Crash-Loop Limiter will throttle restarts after 3 consecutive crashes and enter a cooldown backoff.
3. Review worker logs at `backend/storage/worker_logs/<worker_name>.log`.
4. Trigger manual restart via WorkerManager if root cause is resolved.

### Scenario C: Unsigned VTK Native DLL Blocked on Windows Host
1. Check if host security policy (WDAC / AppLocker) blocked native VTK C++ libraries.
2. The Gateway will gracefully degrade and return `503 WORKER_UNAVAILABLE` on Face inference requests without crashing.
3. For continuous operation, deploy the Face worker in a Linux/Docker container as detailed in `OPERATIONS_RUNBOOK.md`.

