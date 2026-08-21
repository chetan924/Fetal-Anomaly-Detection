import logging
import requests

logger = logging.getLogger(__name__)


# ============================================================
# BREVO HTTPS API CONFIGURATION
# ============================================================

from app.core.config import (
    BREVO_API_KEY,
    EMAIL_FROM_ADDRESS,
    EMAIL_FROM_NAME,
)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """
    Send email using Brevo's HTTPS Email API (v3).
    No outbound SMTP port or custom domain required.
    """

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if not BREVO_API_KEY:
        raise RuntimeError(
            "BREVO_API_KEY is not configured."
        )

    if not EMAIL_FROM_ADDRESS:
        raise RuntimeError(
            "EMAIL_FROM_ADDRESS is not configured."
        )

    if not to_email:
        raise ValueError(
            "Recipient email is required."
        )

    # --------------------------------------------------------
    # Build payload
    # --------------------------------------------------------

    html_body = body.replace("\n", "<br>")
    html_content = (
        "<!DOCTYPE html><html><body style='font-family: Arial, sans-serif; "
        f"line-height: 1.6; color: #1e293b;'>{html_body}</body></html>"
    )

    payload = {
        "sender": {
            "name": EMAIL_FROM_NAME or "FetalAI Clinical AI Platform",
            "email": EMAIL_FROM_ADDRESS.strip(),
        },
        "to": [
            {
                "email": to_email.strip(),
            }
        ],
        "subject": subject,
        "textContent": body,
        "htmlContent": html_content,
    }

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # --------------------------------------------------------
    # Send via HTTPS API
    # --------------------------------------------------------

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        logger.error("Unable to connect to Brevo email API: %s", exc)
        raise RuntimeError(
            "Unable to connect to Brevo email API."
        ) from exc

    # --------------------------------------------------------
    # Handle Brevo API response
    # --------------------------------------------------------

    if not response.ok:
        try:
            error_data = response.json()
        except ValueError:
            error_data = response.text

        logger.error(
            "Brevo email API failed: HTTP %s - %s",
            response.status_code,
            error_data,
        )
        raise RuntimeError(
            f"Brevo email API failed: HTTP {response.status_code} - {error_data}"
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
    Send OTP email via Brevo HTTPS Email API.
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