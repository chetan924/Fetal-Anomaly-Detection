# FetalAI — Production Deployment & Infrastructure Guide

## 1. System Architecture Overview

FetalAI operates a decoupled, failure-tolerant architecture designed for high availability, security, and low memory consumption (~512 MB RAM footprint):

```
+-------------------------------------------------------------+
|                      Client Browser                         |
|                   (React + Vite on :5173)                   |
+------------------------------+------------------------------+
                               | HTTPS / WSS
                               v
+-------------------------------------------------------------+
|               FetalAI Main API Gateway (:8000)              |
|        FastAPI / Python 3.10 / ML-Free Baseline (<80 MB)     |
|  - RateLimitingMiddleware (In-Memory Sliding Window)        |
|  - SecurityHeadersMiddleware (CSP, HSTS, X-Frame-Options)   |
|  - RequestId & Structured Audit Logging                     |
|  - Role-Based Access Control & IDOR Validation              |
|  - WorkerLifecycleManager (On-Demand & Idle Reaper)         |
+------------------------------+------------------------------+
         |                     |                      |
         v                     v                      v
+-----------------+   +------------------+   +----------------+
| Neon PostgreSQL |   | Brevo Email API  |   | Storage System |
| (Pooler / SSL)  |   | (HTTPS port 443) |   | (Scans/Logs)   |
+-----------------+   +------------------+   +----------------+
                               |
            On-Demand Subprocess Spawning & Reaping
                               |
+-------------------------------------------------------------+
|               Specialized ML Worker Processes               |
|  - Plane Worker (:8100, Python 3.10)                        |
|  - Spine Worker (:8101, Python 3.10)                        |
|  - Brain Worker (:8102, Python 3.10)                        |
|  - Lung Worker (:8103, Python 3.10)                         |
|  - Bone Worker (:8105, Python 3.10)                         |
|  - Placenta Worker (:8106, Python 3.10)                     |
|  - Face Worker (:8107, Python 3.11 + VTK)                   |
|  - Heart Worker (:8108, Python 3.10)                        |
|  - Kidney Worker (:8109, DISABLED — Model Unavailable)      |
+-------------------------------------------------------------+
```

---

## 2. Memory Optimization & 512 MB RAM Target Strategy

1. **ML-Free Gateway**: The main FastAPI gateway process imports **zero** ML frameworks (`torch`, `ultralytics`, `vtk`, `cv2`, `tensorflow`, `sklearn`). Baseline memory is strictly `< 80 MB`.
2. **Single Process Gateway (`--workers 1`)**: Multi-worker uvicorn multiplies baseline memory and creates duplicate worker managers. Production must run with `--workers 1`.
3. **On-Demand Worker Spawning**: Specialized ML workers are launched **only when an inference request arrives** for that anatomical plane.
4. **Idle Worker Reaping**: A background reaper task checks worker processes every 5 seconds. Any worker that has been idle for $> 300\text{s}$ (`WORKER_IDLE_TIMEOUT_SECONDS`) is gracefully terminated (`SIGTERM`), immediately freeing RAM.
5. **In-Memory Rate Limiting**: Sliding-window tracking uses pure Python collections with periodic garbage collection, consuming `< 1 MB` RAM without external Redis dependencies.
6. **Database Connection Pool**: Configured with `pool_size=5`, `max_overflow=10`, `pool_recycle=1800`, `pool_pre_ping=True` to prevent connection leaks.

---

## 3. Environment Variables & Fail-Fast Validation

The gateway validates all environment variables on boot. If any required secret is missing, too weak, or using a default placeholder in `ENVIRONMENT=production`, the process **fails fast and refuses to boot**.

| Variable | Type | Default | Production Requirement |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | `string` | `development` | Set to `production` |
| `API_HOST` | `string` | `0.0.0.0` | Bind host address |
| `PORT` / `API_PORT` | `int` | `8000` | Gateway listening port |
| `FRONTEND_URL` | `string` | `http://localhost:5173` | **Must start with `https://`** |
| `FRONTEND_ORIGINS` | `string` | `""` | Comma-separated extra HTTPS origins |
| `JWT_SECRET_KEY` | `string` | `""` | **>= 32 chars**, non-default secret |
| `JWT_ALGORITHM` | `string` | `HS256` | Must be `HS256`, `HS384`, or `HS512` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `int` | `30` | Access token lifespan |
| `LOGIN_OTP_ENABLED` | `bool` | `false` | Enable/disable 2FA OTP |
| `POSTGRES_HOST` | `string` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `int` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `string` | `fetalai` | PostgreSQL database name |
| `POSTGRES_USER` | `string` | `fetalai` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `string` | `""` | **Must be non-empty** |
| `DB_POOL_SIZE` | `int` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `int` | `10` | Max overflow connections |
| `BREVO_API_KEY` | `string` | `""` | **Must be set in production** |
| `EMAIL_FROM_ADDRESS` | `string` | `""` | **Must be set in production** |
| `EMAIL_FROM_NAME` | `string` | `FetalAI Clinical AI Platform` | Email sender name |
| `RATE_LIMIT_ENABLED` | `bool` | `true` | Enable rate limiting |
| `RATE_LIMIT_AUTH_PER_MINUTE` | `int` | `10` | Max auth requests/min |
| `RATE_LIMIT_INFERENCE_PER_MINUTE`| `int` | `20` | Max inference requests/min |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | `int` | `60` | Max general requests/min |
| `SECURITY_HEADERS_ENABLED` | `bool` | `true` | Enforce security headers |
| `HSTS_ENABLED` | `bool` | `true` (prod) | Enforce HSTS |
| `MAX_UPLOAD_SIZE_BYTES` | `int` | `15728640` (15 MB) | Max scan file upload size |

---

## 4. Health Probes & Monitoring Endpoints

FetalAI exposes three distinct health probes for load balancers, orchestrators, and monitoring agents:

### 4.1 Liveness Probe (`GET /health`)
- Verifies that the FastAPI gateway event loop and HTTP server are responsive.
- Does not query external dependencies.
- **Expected Status**: `200 OK`
- **Response**: `{"status": "ok", "service": "backend", "environment": "production"}`

### 4.2 Readiness Probe (`GET /health/readiness`)
- Performs a lightweight `SELECT 1` ping against the PostgreSQL database.
- **Expected Status**: `200 OK` (when DB connected) or `503 Service Unavailable` (if DB down).
- **Healthy Response**: `{"status": "ready", "database": "connected", "workers": "available"}`
- **Unhealthy Response**: `{"status": "unhealthy", "database": "disconnected", "error": "..."}`

### 4.3 Worker Status Probe (`GET /health/workers`)
- Inspects active worker child processes, process IDs, and idle counters without starting unstarted workers.
- Reports disabled workers (e.g. `kidney: {state: "disabled", reason: "model unavailable"}`).
- **Expected Status**: `200 OK`

---

## 5. Security & Isolation Defenses

1. **Security Headers**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
   - `Content-Security-Policy: default-src 'self'; ... frame-ancestors 'none';`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (enforced on HTTPS)
2. **CORS Isolation**: In production (`ENVIRONMENT=production`), localhost origins are strictly forbidden. Only explicitly configured HTTPS origins are permitted.
3. **IDOR & Object-Level Authorization**: Every database access (`GET /patients/{id}`, `GET /scans/{id}`, `GET /reports/{id}`, `GET /analysis-sessions/{id}`) verifies ownership against `current_user.id` or checks `current_user.role == "admin"`. Cross-user access returns `403 Forbidden` and logs a structured security audit event.
4. **Path Traversal Sanitization**: All file downloads and storage accesses validate paths with `Path.resolve().relative_to(STORAGE_DIR)` to completely prevent directory traversal attacks.
5. **Zero Information Leakage**: Production 500 handlers return generic error envelopes (`{"detail": "An internal server error occurred.", "request_id": "req_..."}`) and suppress internal stack traces from client responses.

---

## 6. Deployment Procedures

### 6.1 Containerized Deployment (Docker)

```bash
# 1. Build the hardened container image
docker build -t fetalai-backend:latest -f backend/Dockerfile backend/

# 2. Run container with environment file and resource limit (512 MB)
docker run -d \
  --name fetalai-backend \
  --restart unless-stopped \
  -m 512m \
  --memory-swap 512m \
  -p 8000:8000 \
  --env-file .env \
  fetalai-backend:latest
```

### 6.2 Cloud PaaS (Render / Railway)

1. **Build Command**: `pip install -r requirements.txt`
2. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` (or use `backend/Procfile`)
3. **Health Check Path**: `/health`
4. **Environment Variables**: Populate all production keys specified in `.env.example`.

---

## 7. Database Maintenance & Backup Runbook

### 7.1 Manual Database Backup
```bash
pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -F c -b -v -f fetalai_backup_$(date +%Y%m%d_%H%M%S).dump
```

### 7.2 Database Restore
```bash
pg_restore -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -v -c fetalai_backup_YYYYMMDD_HHMMSS.dump
```

### 7.3 Alembic Schema Migrations
```bash
cd backend
alembic upgrade head
```

---

## 8. Incident Response & Troubleshooting

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| Gateway crashes on startup | Missing/invalid production secret or weak JWT | Check container logs for `RuntimeError`. Verify `.env` parameters against Section 3. |
| `503 Service Unavailable` on `/health/readiness` | Database unreachable or SSL handshake failure | Verify PostgreSQL host, credentials, and network connectivity. |
| `429 Too Many Requests` | Client exceeded sliding window rate limit | Inspect `Retry-After` response header. Adjust rate limits in `.env` if legitimate burst. |
| Worker inference times out | Heavy model initialization or RAM exhaustion | Check `storage/worker_logs/<worker>_worker.log`. Ensure instance has minimum 512 MB RAM. |
| Stale session on startup | Gateway rebooted during active multi-worker scan | Gateway automatically runs `recover_stale_sessions()` on boot to mark interrupted sessions `failed`. |
