# ============================================================
# FETALAI EMAIL SERVICE
# RESEND HTTP API
# ============================================================

import requests


# ============================================================
# RESEND CONFIGURATION
# ============================================================

from app.core.config import (
    RESEND_API_KEY,
    RESEND_FROM_EMAIL,
    RESEND_FROM_NAME,
)


RESEND_API_URL = "https://api.resend.com/emails"


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """
    Send email using Resend HTTP API.

    No SMTP connection is used.
    """

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if not RESEND_API_KEY:
        raise RuntimeError(
            "RESEND_API_KEY is not configured."
        )

    if not RESEND_FROM_EMAIL:
        raise RuntimeError(
            "RESEND_FROM_EMAIL is not configured."
        )

    if not RESEND_FROM_NAME:
        raise RuntimeError(
            "RESEND_FROM_NAME is not configured."
        )

    if not to_email:
        raise ValueError(
            "Recipient email is required."
        )

    # --------------------------------------------------------
    # Prepare request
    # --------------------------------------------------------

    payload = {
        "from": (
            f"{RESEND_FROM_NAME} "
            f"<{RESEND_FROM_EMAIL}>"
        ),
        "to": [
            to_email.strip()
        ],
        "subject": subject,
        "text": body,
    }

    headers = {
        "Authorization": (
            f"Bearer {RESEND_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    # --------------------------------------------------------
    # Send through Resend HTTP API
    # --------------------------------------------------------

    try:

        response = requests.post(
            RESEND_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

    except requests.RequestException as exc:

        raise RuntimeError(
            "Unable to connect to Resend email API."
        ) from exc

    # --------------------------------------------------------
    # Handle Resend errors
    # --------------------------------------------------------

    if not response.ok:

        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        raise RuntimeError(
            "Resend email API failed: "
            f"HTTP {response.status_code} - "
            f"{error_data}"
        )


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(
    to_email: str,
    otp: str,
    purpose: str = "verification",
) -> None:
    """
    Send OTP email using Resend.
    """

    normalized_purpose = (
        purpose or "verification"
    ).strip().lower()

    # --------------------------------------------------------
    # LOGIN OTP
    # --------------------------------------------------------

    if normalized_purpose in {
        "login",
        "login_otp",
        "signin",
        "sign_in",
    }:

        subject = (
            "FetalAI - Login Verification Code"
        )

        message = (
            "Your FetalAI login verification code "
            "is:\n\n"
            f"{otp}\n\n"
            "This code will expire in 10 minutes.\n\n"
            "If you did not try to sign in, "
            "you can safely ignore this email.\n\n"
            "FetalAI Clinical AI Platform"
        )

    # --------------------------------------------------------
    # SIGNUP OTP
    # --------------------------------------------------------

    elif normalized_purpose in {
        "signup",
        "register",
        "registration",
        "signup_otp",
    }:

        subject = (
            "FetalAI - Account Verification Code"
        )

        message = (
            "Your FetalAI account verification code "
            "is:\n\n"
            f"{otp}\n\n"
            "This code will expire in 10 minutes.\n\n"
            "Please do not share this code with anyone.\n\n"
            "FetalAI Clinical AI Platform"
        )

    # --------------------------------------------------------
    # PASSWORD RESET OTP
    # --------------------------------------------------------

    elif normalized_purpose in {
        "forgot_password",
        "password_reset",
        "reset_password",
        "forgot",
    }:

        subject = (
            "FetalAI - Password Reset Code"
        )

        message = (
            "Your FetalAI password reset verification "
            "code is:\n\n"
            f"{otp}\n\n"
            "This code will expire in 10 minutes.\n\n"
            "If you did not request a password reset, "
            "you can safely ignore this email.\n\n"
            "FetalAI Clinical AI Platform"
        )

    # --------------------------------------------------------
    # GENERIC OTP
    # --------------------------------------------------------

    else:

        subject = (
            "FetalAI - Verification Code"
        )

        message = (
            "Your FetalAI verification code is:\n\n"
            f"{otp}\n\n"
            "This code will expire in 10 minutes.\n\n"
            "Please do not share this code with anyone.\n\n"
            "FetalAI Clinical AI Platform"
        )

    # --------------------------------------------------------
    # SEND
    # --------------------------------------------------------

    send_email(
        to_email=to_email,
        subject=subject,
        body=message,
    )