import os
from pathlib import Path

from dotenv import load_dotenv


# =========================================================
# PROJECT ROOT
# =========================================================
#
# config.py:
# backend/app/core/config.py
#
# parents[0] -> core
# parents[1] -> app
# parents[2] -> backend
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# =========================================================
# ENVIRONMENT FILE
# =========================================================

ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)


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
        os.getenv("PORT") or os.getenv("API_PORT") or "8000"
    )
except ValueError as exc:
    raise RuntimeError(
        "API_PORT / PORT must be a valid integer."
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
# LOGIN OTP
# =========================================================

LOGIN_OTP_ENABLED = os.getenv(
    "LOGIN_OTP_ENABLED",
    "false",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


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
# =========================================================
# SMTP EMAIL  (Gmail App Password — no custom domain)
# =========================================================
#
# Uses Python stdlib smtplib over STARTTLS on port 587.
# No new pip packages required.
#
# Render environment variables required:
#   SMTP_HOST     (default: smtp.gmail.com)
#   SMTP_PORT     (default: 587)
#   SMTP_USERNAME (your Gmail address)
#   SMTP_PASSWORD (Gmail App Password — NOT your login password)
#   EMAIL_FROM_NAME (display name, optional)
# =========================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com",
).strip()

try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
except ValueError as exc:
    raise RuntimeError("SMTP_PORT must be a valid integer.") from exc

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    "",
).strip()

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    "",
).strip()

EMAIL_FROM_NAME = os.getenv(
    "EMAIL_FROM_NAME",
    "FetalAI Clinical AI Platform",
).strip()


# =========================================================
# SMTP BASIC VALIDATION
# =========================================================




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
        "YOUR_32_PLUS_CHARACTER_SECRET",
    }:
        raise RuntimeError(
            "A default/insecure JWT secret cannot "
            "be used in production."
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
    # SMTP CREDENTIALS
    # -----------------------------------------------------

    if not SMTP_USERNAME:
        raise RuntimeError(
            "SMTP_USERNAME must be set "
            "in production."
        )

    if not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_PASSWORD must be set "
            "in production."
        )


# =========================================================
# CONFIGURATION SUMMARY
# =========================================================
#
# NEVER print:
# - PostgreSQL password
# - JWT secret
# - SMTP_PASSWORD
#
# =========================================================

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
    "Login OTP enabled:",
    LOGIN_OTP_ENABLED,
)


print(
    "SMTP host:",
    SMTP_HOST,
)


print(
    "SMTP port:",
    SMTP_PORT,
)


print(
    "SMTP username configured:",
    bool(SMTP_USERNAME),
)


print(
    "Email from name:",
    EMAIL_FROM_NAME,
)


print("=" * 60)
print()
