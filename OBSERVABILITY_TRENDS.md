# FetalAI v1.0 — Production Observability Trends & Degradation Signals

**Version**: 1.0  
**Classification**: Site Reliability Engineering (SRE) & Operational Health  
**Last Updated**: `2026-09-21T20:10:00Z`  

---

## 1. Metric Telemetry & Degradation Thresholds

FetalAI utilizes deterministic rule-based degradation detection across all critical paths:

| Subsystem | Metric Monitored | Healthy Baseline | Warning Threshold | Critical Threshold |
|---|---|---|---|---|
| **API Gateway** | HTTP Request Latency | $< 500\text{ ms}$ | $\ge 2,000\text{ ms}$ | $\ge 5,000\text{ ms}$ |
| **API Gateway** | HTTP 5xx Error Rate | $0.0\%$ | $\ge 1.0\%$ | $\ge 5.0\%$ |
| **API Gateway** | Process RSS Memory | $< 150\text{ MB}$ | $\ge 400\text{ MB}$ | $\ge 750\text{ MB}$ |
| **Database Pool** | Readiness Ping Latency | $< 1,500\text{ ms}$ | $\ge 2,500\text{ ms}$ | $\ge 5,000\text{ ms}$ (Timeout) |
| **Database Pool** | Connection Failure | $0$ failures | $1$ failed ping | Consecutive drops |
| **ML Worker Fleet** | Worker Process Restarts | $0$ crashes | $2$ crashes in $60\text{s}$ | $3$ crashes (Crash-Loop) |
| **ML Worker Fleet** | Single Inference Latency | $< 4,000\text{ ms}$ | $\ge 10,000\text{ ms}$ | $\ge 20,000\text{ ms}$ |
| **Reporting Engine**| 16-Section PDF Generation | $< 2,000\text{ ms}$ | $\ge 5,000\text{ ms}$ | Binary stream failure |
| **Backup Storage** | Database Snapshot Age | $< 12\text{ hours}$ | $\ge 24\text{ hours}$ | $\ge 48\text{ hours}$ |
| **Backup Storage** | Storage Volume Snapshot Age | $< 12\text{ hours}$ | $\ge 24\text{ hours}$ | $\ge 48\text{ hours}$ |

---

## 2. Telemetry Endpoints Reference

### `/health`
- **Purpose**: Lightweight process liveness, memory posture, active alert count.
- **Latency**: $< 5\text{ ms}$.
- **Response Example**:
  ```json
  {
    "status": "ok",
    "app": "FetalAI Clinical AI Platform",
    "environment": "development",
    "version": "1.0.0",
    "health_status": "HEALTHY",
    "memory": {
      "rss_mb": 91.38,
      "high_memory_threshold_mb": 400.0,
      "is_high_memory_pressure": false
    }
  }
  ```

### `/health/readiness`
- **Purpose**: End-to-end readiness probe for ingress load balancers. Validates database pool pre-ping.
- **Response Example**:
  ```json
  {
    "status": "ready",
    "database": "connected",
    "database_latency_ms": 972.19,
    "workers_registered": 10,
    "disabled_workers": ["kidney"]
  }
  ```

### `/health/workers`
- **Purpose**: Real-time worker process status, PID mapping, ports, crash counts, and backoff states.
- **Response Example**:
  ```json
  {
    "workers": {
      "plane": {"port": 8100, "state": "healthy", "crashes": 0},
      "spine": {"port": 8101, "state": "healthy", "crashes": 0},
      "kidney": {"port": 8109, "status": "disabled", "disabled_reason": "model unavailable"}
    }
  }
  ```

### `/health/alerts`
- **Purpose**: Operational alert dashboard. Reports firing and recently resolved alerts with deduplication counters.
- **Response Example**:
  ```json
  {
    "overall_status": "HEALTHY",
    "active_alert_count": 0,
    "active_alerts": [],
    "recent_resolved_alerts": []
  }
  ```

### `/health/metrics`
- **Purpose**: Sanitized operational counters, latency averages, request distributions, and session transitions.

---

## 3. Degradation Response Runbook

1. **Slow Request Degradation ($> 2,000\text{ ms}$)**:
   - Check `/health/metrics` top endpoints.
   - If concentrated in a single worker (e.g. `brain` or `spine`), inspect child worker log at `backend/storage/worker_logs/{worker}_worker.log`.
2. **Database Latency Degradation ($> 2,500\text{ ms}$)**:
   - Check Neon Cloud console for compute scaling or replication lag.
   - Verify connection pool health in `/health/readiness`.
3. **Worker Crash-Loop Backoff**:
   - Check `/health/workers` for worker state `crash_loop_backoff`.
   - The worker enters a 30s cooldown backoff. Review model weights integrity in `backend/app/ml/models/`.
4. **Stale Backup Warning ($> 24\text{ hours}$)**:
   - Trigger the automated maintenance script:
     ```bash
     py -3.10 "scratch/automated_maintenance_suite.py"
     ```

