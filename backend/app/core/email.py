import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


# ============================================================
# SMTP CONFIGURATION  (Gmail App Password)
# ============================================================

from app.core.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM_NAME,
)


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:
    """
    Send email via Gmail SMTP (TLS, port 587).
    Requires a Gmail account with an App Password.
    No custom domain required.
    """

    # --------------------------------------------------------
    # Validate configuration
    # --------------------------------------------------------

    if not SMTP_USERNAME:
        raise RuntimeError(
            "SMTP_USERNAME is not configured."
        )

    if not SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP_PASSWORD is not configured."
        )

    if not to_email:
        raise ValueError(
            "Recipient email is required."
        )

    # --------------------------------------------------------
    # Build message
    # --------------------------------------------------------

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = (
        f"{EMAIL_FROM_NAME} <{SMTP_USERNAME}>"
        if EMAIL_FROM_NAME
        else SMTP_USERNAME
    )
    msg["To"] = to_email.strip()
    msg.attach(MIMEText(body, "plain"))

    # --------------------------------------------------------
    # Send via SMTP
    # --------------------------------------------------------

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(
                SMTP_USERNAME,
                to_email.strip(),
                msg.as_string(),
            )

    except smtplib.SMTPAuthenticationError as exc:
        logger.error(
            "SMTP authentication failed for sender '%s': %s",
            SMTP_USERNAME,
            exc,
        )
        raise RuntimeError(
            "Email authentication failed. "
            "Check SMTP_USERNAME and SMTP_PASSWORD."
        ) from exc

    except smtplib.SMTPException as exc:
        logger.error(
            "SMTP error while sending to '%s': %s",
            to_email,
            exc,
        )
        raise RuntimeError(
            "Unable to send email via SMTP."
        ) from exc

    except OSError as exc:
        logger.error(
            "SMTP connection error to %s:%s — %s",
            SMTP_HOST,
            SMTP_PORT,
            exc,
        )
        raise RuntimeError(
            "Unable to connect to SMTP server."
        ) from exc





# ============================================================
# SEND OTP EMAIL
# ============================================================

def send_otp_email(
    to_email: str,
    otp: str,
    purpose: str = "verification",
) -> None:
    """
    Send OTP email via Gmail SMTP.

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