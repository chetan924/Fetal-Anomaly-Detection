from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.ai import router as ai_router
from app.api.scans import router as scans_router
from app.api.auth import router as auth_router
from app.api.patients import router as patients_router

from app.core.config import (
    ENVIRONMENT,
    FRONTEND_URL,
)

from app.db.database import (
    Base,
    engine,
)

from app.models.user import User
from app.models.patient import Patient
from app.models.scan import Scan


# =========================================================
# ENVIRONMENT
# =========================================================

# config.py already loads backend/.env explicitly.
# load_dotenv() is retained as a harmless fallback
# for the process environment.
load_dotenv()


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="FetalAI API",
    version="0.1.0",
    description=(
        "AI-assisted fetal anomaly "
        "screening prototype API"
    ),
)


# =========================================================
# PATH CONFIGURATION
# =========================================================

APP_DIR = (
    Path(__file__)
    .resolve()
    .parent
)

BACKEND_ROOT = (
    APP_DIR.parent
)


# =========================================================
# STORAGE DIRECTORIES
# =========================================================

STORAGE_DIR = (
    BACKEND_ROOT
    / "storage"
)

SCAN_STORAGE_DIR = (
    STORAGE_DIR
    / "scans"
)

EXPLAINABILITY_STORAGE_DIR = (
    STORAGE_DIR
    / "explainability"
)


# =========================================================
# CREATE STORAGE DIRECTORIES
# =========================================================

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

SCAN_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXPLAINABILITY_STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# STORAGE DEBUG INFORMATION
# =========================================================

# Do not print secrets or user data here.
# Paths are safe to expose in development logs.
# Keep production logs quieter.

if ENVIRONMENT != "production":

    print()
    print("=" * 60)
    print("FETALAI STORAGE CONFIGURATION")
    print("=" * 60)

    print(
        "App directory:",
        APP_DIR,
    )

    print(
        "Backend root:",
        BACKEND_ROOT,
    )

    print(
        "Storage directory:",
        STORAGE_DIR,
    )

    print(
        "Scan directory:",
        SCAN_STORAGE_DIR,
    )

    print(
        "Explainability directory:",
        EXPLAINABILITY_STORAGE_DIR,
    )

    print(
        "Storage exists:",
        STORAGE_DIR.exists(),
    )

    print(
        "Scans exists:",
        SCAN_STORAGE_DIR.exists(),
    )

    print(
        "Explainability exists:",
        EXPLAINABILITY_STORAGE_DIR.exists(),
    )

    print("=" * 60)
    print()


# =========================================================
# STATIC STORAGE
# =========================================================

app.mount(
    "/storage",
    StaticFiles(
        directory=str(
            STORAGE_DIR
        ),
        check_dir=True,
    ),
    name="storage",
)


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# CORS CONFIGURATION
# =========================================================

# Production frontend
allowed_origins = [
    "https://fetal-anomaly-detection.onrender.com",
]


# =========================================================
# FRONTEND_URL FROM CONFIG
# =========================================================

if FRONTEND_URL:
    allowed_origins.append(
        FRONTEND_URL.strip()
    )


# =========================================================
# LOCAL DEVELOPMENT ORIGINS
# =========================================================

if ENVIRONMENT != "production":

    allowed_origins.extend(
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )


# =========================================================
# REMOVE DUPLICATE / EMPTY ORIGINS
# =========================================================

allowed_origins = list(
    dict.fromkeys(
        origin.strip()
        for origin in allowed_origins
        if origin
        and origin.strip()
    )
)


# =========================================================
# CORS MIDDLEWARE
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=allowed_origins,

    allow_credentials=True,

    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],

    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
    ],
)


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    patients_router
)

app.include_router(
    ai_router
)

app.include_router(
    scans_router
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get(
    "/health"
)
def health_check() -> dict[str, str]:

    return {
        "status": "ok",
        "service": "backend",
    }


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def root() -> dict[str, str]:

    return {
        "message":
            "FetalAI backend is running",
    }