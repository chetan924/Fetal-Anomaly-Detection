import os

import psycopg
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import (
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_HOST,
    POSTGRES_PORT,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
    DB_POOL_RECYCLE,
    DB_POOL_PRE_PING,
)


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

load_dotenv()

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=require"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def _create_psycopg_connection():
    """
    Create a PostgreSQL connection using psycopg directly.

    Direct psycopg connectivity has already been verified
    successfully on this machine.
    """

    return psycopg.connect(
        host=POSTGRES_HOST,
        port=int(POSTGRES_PORT),
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        sslmode="require",
        connect_timeout=10,
    )


# ============================================================
# SQLALCHEMY ENGINE
# ============================================================

engine = create_engine(
    "postgresql+psycopg://",
    creator=_create_psycopg_connection,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=DB_POOL_PRE_PING,
)


# ============================================================
# SESSION
# ============================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# BASE
# ============================================================

Base = declarative_base()


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# READINESS PROBE HELPER
# ============================================================

def check_database_connection() -> tuple[bool, str | None]:
    """
    Lightweight DB ping for readiness checks (SELECT 1).
    Returns (True, None) if healthy, or (False, error_message).
    """
    import time
    t0 = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.time() - t0) * 1000, 2)
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_db_ping(latency_ms=latency_ms, success=True)
        except Exception:
            pass
        return True, None
    except Exception as exc:
        latency_ms = round((time.time() - t0) * 1000, 2)
        try:
            from app.core.metrics import metrics_collector
            metrics_collector.record_db_ping(latency_ms=latency_ms, success=False, error=str(exc))
        except Exception:
            pass
        return False, str(exc)
