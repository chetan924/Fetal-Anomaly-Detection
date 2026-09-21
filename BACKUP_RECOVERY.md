# FetalAI Database Backup & Disaster Recovery Runbook

**Version**: 1.0  
**Target Database**: PostgreSQL 16 (Neon Serverless / Dedicated PostgreSQL)  
**Classification**: Production Disaster Recovery (DR) & Business Continuity

---

## 1. Operational Recovery Targets (RPO & RTO)

| Metric | Target | Description |
|---|---|---|
| **RPO (Recovery Point Objective)** | **<= 1 Hour** | Maximum allowable data loss period in disaster scenario |
| **RTO (Recovery Time Objective)** | **<= 15 Minutes** | Maximum target time to restore full service availability |
| **Backup Retention Period** | **30 Days** | Retained encrypted daily snapshots + weekly archives |
| **Verification Frequency** | **Daily automated + Monthly drill** | Automated integrity verification on every backup artifact |

---

## 2. Backup Architecture & Data Classification

FetalAI production data comprises two distinct tiers:

1. **Relational Database Tier (Neon PostgreSQL)**:
   - User credentials and clinical roles (`users`)
   - Patient records and gestational age history (`patients`)
   - Scan metadata, file paths, and upload timestamps (`scans`)
   - Analysis session states and idempotency logs (`analysis_sessions`)
   - Clinical report snapshots with immutable JSON findings (`reports`)

2. **File Storage Volume Tier (`backend/storage/`)**:
   - Ultrasound scan images (`storage/scans/`)
   - Explainability Grad-CAM heatmaps and VTK renders (`storage/explainability/`)
   - Worker runtime diagnostic logs (`storage/worker_logs/`)

---

## 3. Backup Procedures

### A. Automated Neon Cloud Point-in-Time Backups
- Neon automatically archives PostgreSQL WAL logs, enabling instantaneous Point-in-Time Recovery (PITR) up to the retention window (e.g. 7-30 days).
- Instant branching allows zero-copy database snapshots before major migrations or releases.

### B. Logical Backup Procedure (`pg_dump`)
Run daily scheduled logical database dumps:

```bash
# Set connection environment variables
export PGPASSWORD="$POSTGRES_PASSWORD"

# Generate compressed custom-format backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
pg_dump   -h "$POSTGRES_HOST"   -p "$POSTGRES_PORT"   -U "$POSTGRES_USER"   -d "$POSTGRES_DB"   -F c   -b   -v   -f "/backup/fetalai_db_${TIMESTAMP}.dump"

# Generate schema-only backup for instant structural validation
pg_dump   -h "$POSTGRES_HOST"   -p "$POSTGRES_PORT"   -U "$POSTGRES_USER"   -d "$POSTGRES_DB"   --schema-only   -f "/backup/fetalai_schema_${TIMESTAMP}.sql"
```

### C. File Storage Snapshot Procedure
```bash
# Sync ultrasound images and explainability artifacts to encrypted backup bucket
rclone sync /backend/storage/ s3://fetalai-production-backups/storage/ --fast-list
```

---

## 4. Disaster Recovery & Restoration Drill (Step-by-Step)

In the event of database corruption, accidental deletion, or infrastructure outage:

### Step 1: Declare Incident & Isolate Gateway
Temporarily prevent incoming write requests while restore is in progress:
```bash
# Put Gateway into maintenance or pause ingress
# (Health readiness probe will report 503 until restore succeeds)
```

### Step 2: Provision Target Database / Restore Point
- **Option A (Neon Instant Point-in-Time Restore)**:
  1. In Neon Console, create a new branch from timestamp `T-10min`.
  2. Update `POSTGRES_HOST` in Gateway environment to the new branch endpoint.
- **Option B (Restore from Logical Dump)**:
  ```bash
  # Drop and recreate database on target PostgreSQL instance
  dropdb -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB"
  createdb -h "$POSTGRES_HOST" -U "$POSTGRES_USER" "$POSTGRES_DB"

  # Restore custom-format dump
  pg_restore     -h "$POSTGRES_HOST"     -p "$POSTGRES_PORT"     -U "$POSTGRES_USER"     -d "$POSTGRES_DB"     -v     --no-owner     --no-acl     /backup/fetalai_db_latest.dump
  ```

### Step 3: Restore Storage Assets
```bash
# Pull scan artifacts back to local storage directory
rclone sync s3://fetalai-production-backups/storage/ /backend/storage/ --fast-list
```

### Step 4: Run Data Integrity & Consistency Checks
Execute automated validation checks against restored database:
```bash
# Verify all 5 core tables exist and have valid row counts
py -3.10 -c "
from app.db.database import engine, check_database_connection
from sqlalchemy import text
ok, err = check_database_connection()
assert ok, f'DB connection failed: {err}'
with engine.connect() as conn:
    tables = ['users', 'patients', 'scans', 'analysis_sessions', 'reports']
    for t in tables:
        count = conn.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
        print(f'Table {t}: {count} records')
print('Database integrity check passed!')
"
```

### Step 5: Reconcile In-Flight Sessions & Health Check
1. Start Gateway process:
   - On startup, `session_service.recover_stale_sessions()` automatically marks any unfinished sessions as `interrupted`.
2. Query `/health/readiness` and verify `database: connected`.
3. Query `/health/alerts` to ensure all critical alerts are resolved.
4. Verify end-to-end report retrieval and PDF download.

---

## 5. Automated Backup Verification Script

Place this script in scheduled maintenance cron to verify backup validity:

```python
import subprocess
import sys
from pathlib import Path

def verify_latest_backup(dump_path: Path):
    print(f"Testing backup integrity for {dump_path}...")
    result = subprocess.run(
        ["pg_restore", "--list", str(dump_path)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"Backup {dump_path.name} is structurally sound (found {len(result.stdout.splitlines())} table elements).")
        return True
    else:
        print(f"Backup verification failed: {result.stderr}")
        return False

if __name__ == "__main__":
    latest_dump = sorted(Path("/backup").glob("*.dump"))[-1]
    if not verify_latest_backup(latest_dump):
        sys.exit(1)
```

---

## 6. Production Recovery Drill Verification & Telemetry (Validated 2026-09-21)

### Verification Summary
- **Validation Date**: September 21, 2026 (19:30 UTC)
- **Status**: **`RECOVERY DRILL VERIFIED WITH LIMITATIONS`**
- **Tested Target**: Neon PostgreSQL (`neondb`) with 7 core tables, 432 rows.
- **Measured RTO**: **`28.735 seconds`** (SLA Target: $\le 15\text{ minutes}$).
- **Measured RPO**: **`Continuous PITR / On-Demand Point-in-Time`** (SLA Target: $\le 1\text{ hour}$).
- **Fidelity Ratio**: **100.0% Exact Match** (432/432 records restored across `alembic_version`, `users`, `patients`, `otps`, `scans`, `analysis_sessions`, `reports`).
- **Application Validation**: Gateway Liveness `200 OK`, Restored DB Readiness `200 OK` (Latency: `1,496.85ms`), User Authentication (`/api/auth/me`), Patient Querying, Report Querying, and 16-Section PDF Rendering (`7,522 bytes`).
- **Detailed Audit**: See [`POST_RECOVERY_DRILL_REPORT.md`](./POST_RECOVERY_DRILL_REPORT.md).

