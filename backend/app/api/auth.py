import os
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# PROJECT ROOT
# =========================================================

# config.py:
# backend/app/core/config.py
#
# parents[0] -> core
# parents[1] -> app
# parents[2] -> backend

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


# =========================================================
# ENVIRONMENT FILE
# =========================================================

ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(
        dotenv_path=ENV_FILE
    )


# =========================================================
# ENVIRONMENT
# =========================================================

ENVIRONMENT = os.getenv(
    "ENVIRONMENT",
    "development",
).strip().lower()


if ENVIRONMENT not in {
    "development",
    "testing",
    "production",
}:
    raise RuntimeError(
        "ENVIRONMENT must be one of: "
        "development, testing, production."
    )


# =========================================================
# API
# =========================================================

API_HOST = os.getenv(
    "API_HOST",
    "0.0.0.0",
).strip()


try:

    API_PORT = int(
        os.getenv(
            "API_PORT",
            "8000",
        )
    )

except ValueError as exc:

    raise RuntimeError(
        "API_PORT must be a valid integer."
    ) from exc


if not 1 <= API_PORT <= 65535:

    raise RuntimeError(
        "API_PORT must be between 1 and 65535."
    )


# =========================================================
# FRONTEND
# =========================================================

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173",
).strip()


if not FRONTEND_URL:

    raise RuntimeError(
        "FRONTEND_URL must not be empty."
    )


# =========================================================
# POSTGRESQL
# =========================================================

POSTGRES_DB = os.getenv(
    "POSTGRES_DB",
    "fetalai",
).strip()


POSTGRES_USER = os.getenv(
    "POSTGRES_USER",
    "fetalai",
).strip()


POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD",
    "",
)


POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST",
    "localhost",
).strip()


POSTGRES_PORT = os.getenv(
    "POSTGRES_PORT",
    "5432",
).strip()


if not POSTGRES_DB:

    raise RuntimeError(
        "POSTGRES_DB must not be empty."
    )


if not POSTGRES_USER:

    raise RuntimeError(
        "POSTGRES_USER must not be empty."
    )


if not POSTGRES_HOST:

    raise RuntimeError(
        "POSTGRES_HOST must not be empty."
    )


try:

    _postgres_port = int(
        POSTGRES_PORT
    )

except ValueError as exc:

    raise RuntimeError(
        "POSTGRES_PORT must be a valid integer."
    ) from exc


if not 1 <= _postgres_port <= 65535:

    raise RuntimeError(
        "POSTGRES_PORT must be between 1 and 65535."
    )


# =========================================================
# JWT
# =========================================================

JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "",
).strip()


JWT_ALGORITHM = os.getenv(
    "JWT_ALGORITHM",
    "HS256",
).strip().upper()


try:

    ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            "30",
        )
    )

except ValueError as exc:

    raise RuntimeError(
        "ACCESS_TOKEN_EXPIRE_MINUTES "
        "must be a valid integer."
    ) from exc


if ACCESS_TOKEN_EXPIRE_MINUTES <= 0:

    raise RuntimeError(
        "ACCESS_TOKEN_EXPIRE_MINUTES "
        "must be greater than 0."
    )


# =========================================================
# JWT SECURITY VALIDATION
# =========================================================

SUPPORTED_JWT_ALGORITHMS = {
    "HS256",
    "HS384",
    "HS512",
}


if JWT_ALGORITHM not in SUPPORTED_JWT_ALGORITHMS:

    raise RuntimeError(
        "Unsupported JWT_ALGORITHM. "
        "Use HS256, HS384, or HS512."
    )


# =========================================================
# RESEND EMAIL API
# =========================================================
#
# IMPORTANT:
#
# We are NOT using:
# - SMTP
# - Gmail SMTP
# - Port 587
# - smtplib
# - SMTP_USERNAME
# - SMTP_PASSWORD
#
# Email is sent using:
#
# https://api.resend.com/emails
#
# This works through HTTPS and does not require
# SMTP port 587.
# =========================================================

RESEND_API_KEY = os.getenv(
    "RESEND_API_KEY",
    "",
).strip()


RESEND_FROM_EMAIL = os.getenv(
    "RESEND_FROM_EMAIL",
    "onboarding@resend.dev",
).strip()


RESEND_FROM_NAME = os.getenv(
    "RESEND_FROM_NAME",
    "FetalAI Clinical AI Platform",
).strip()


# =========================================================
# RESEND VALIDATION
# =========================================================

if ENVIRONMENT in {
    "testing",
    "production",
}:

    if not RESEND_API_KEY:

        raise RuntimeError(
            "RESEND_API_KEY must be configured."
        )


if not RESEND_FROM_EMAIL:

    raise RuntimeError(
        "RESEND_FROM_EMAIL must not be empty."
    )


if not RESEND_FROM_NAME:

    raise RuntimeError(
        "RESEND_FROM_NAME must not be empty."
    )


# =========================================================
# PRODUCTION SECURITY VALIDATION
# =========================================================

if ENVIRONMENT == "production":

    # -----------------------------------------------------
    # JWT SECRET
    # -----------------------------------------------------

    if not JWT_SECRET_KEY:

        raise RuntimeError(
            "JWT_SECRET_KEY must be set in production."
        )


    if len(JWT_SECRET_KEY) < 32:

        raise RuntimeError(
            "JWT_SECRET_KEY must contain at least "
            "32 characters in production."
        )


    if JWT_SECRET_KEY in {
        "change-me-in-production",
        "secret",
        "secret-key",
    }:

        raise RuntimeError(
            "A default/insecure JWT secret "
            "cannot be used in production."
        )


    # -----------------------------------------------------
    # DATABASE PASSWORD
    # -----------------------------------------------------

    if not POSTGRES_PASSWORD:

        raise RuntimeError(
            "POSTGRES_PASSWORD must be set "
            "in production."
        )


    # -----------------------------------------------------
    # FRONTEND URL
    # -----------------------------------------------------

    if not FRONTEND_URL.startswith(
        "https://"
    ):

        raise RuntimeError(
            "FRONTEND_URL must use HTTPS "
            "in production."
        )


    # -----------------------------------------------------
    # RESEND
    # -----------------------------------------------------

    if not RESEND_API_KEY:

        raise RuntimeError(
            "RESEND_API_KEY must be set "
            "in production."
        )


# =========================================================
# CONFIGURATION SUMMARY
# =========================================================
#
# NEVER print:
# - POSTGRES_PASSWORD
# - JWT_SECRET_KEY
# - RESEND_API_KEY
#
# =========================================================

if ENVIRONMENT != "production":

    print()
    print("=" * 60)
    print("FETALAI CONFIGURATION")
    print("=" * 60)

    print(
        "Environment:",
        ENVIRONMENT,
    )

    print(
        "Project root:",
        PROJECT_ROOT,
    )

    print(
        "Environment file:",
        ENV_FILE,
    )

    print(
        "Environment file exists:",
        ENV_FILE.exists(),
    )

    print(
        "API host:",
        API_HOST,
    )

    print(
        "API port:",
        API_PORT,
    )

    print(
        "Frontend URL:",
        FRONTEND_URL,
    )

    print(
        "PostgreSQL host:",
        POSTGRES_HOST,
    )

    print(
        "PostgreSQL port:",
        POSTGRES_PORT,
    )

    print(
        "PostgreSQL database:",
        POSTGRES_DB,
    )

    print(
        "PostgreSQL user:",
        POSTGRES_USER,
    )

    print(
        "JWT algorithm:",
        JWT_ALGORITHM,
    )

    print(
        "Access token expiry:",
        ACCESS_TOKEN_EXPIRE_MINUTES,
        "minutes",
    )

    print(
        "Resend API key configured:",
        bool(RESEND_API_KEY),
    )

    print(
        "Resend from email:",
        RESEND_FROM_EMAIL,
    )

    print(
        "Resend from name:",
        RESEND_FROM_NAME,
    )

    print("=" * 60)
    print()