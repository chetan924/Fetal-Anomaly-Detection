# ============================================================
# FETALAI EMAIL SERVICE
# ============================================================

import os
import smtplib
from email.message import EmailMessage


# ============================================================
# SMTP CONFIGURATION
# ============================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "smtp.gmail.com",
)

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "587",
    )
)

SMTP_USERNAME = os.getenv(
    "SMTP_USERNAME",
    "",
).strip()

SMTP_PASSWORD = os.getenv(
    "SMTP_PASSWORD",
    "",
).strip()

SMTP_FROM_EMAIL = os.getenv(
    "SMTP_FROM_EMAIL",
    SMTP_USERNAME,
).strip()

SMTP_FROM_NAME = os.getenv(
    "SMTP_FROM_NAME",
    "FetalAI Clinical AI Platform",
).strip()


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:

    if not SMTP_USERNAME:
        raise RuntimeError(
            "SMTP_USERNAME is not configured."
        )

    if not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_PASSWORD is not configured."
        )

    if not SMTP_FROM_EMAIL:
        raise RuntimeError(
            "SMTP_FROM_EMAIL is not configured."
        )

    if not to_email:
        raise ValueError(
            "Recipient email is required."
        )

    message = EmailMessage()

    message["From"] = (
        f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    )

    message["To"] = to_email.strip()

    message["Subject"] = subject

    message.set_content(body)

    try:

        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30,
        ) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(
                SMTP_USERNAME,
                SMTP_PASSWORD,
            )

            server.send_message(message)

    except smtplib.SMTPAuthenticationError as exc:

        raise RuntimeError(
            "SMTP authentication failed. "
            "Check the Gmail address and App Password."
        ) from exc

    except smtplib.SMTPException as exc:

        raise RuntimeError(
            f"SMTP email sending failed: {exc}"
        ) from exc

    except OSError as exc:

        raise RuntimeError(
            f"Unable to connect to SMTP server: {exc}"
        ) from exc


# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(
    to_email: str,
    otp: str,
    purpose: str = "verification",
) -> None:

    normalized_purpose = (
        purpose or "verification"
    ).strip().lower()

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

    send_email(
        to_email=to_email,
        subject=subject,
        body=message,
    )