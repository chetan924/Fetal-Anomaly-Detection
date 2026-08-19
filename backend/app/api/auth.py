import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.email import send_otp_email
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.otp import OTP
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ResetPasswordWithOTPRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    VerifyForgotPasswordOTPRequest,
    VerifyLoginOTPRequest,
    VerifySignupOTPRequest,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ============================================================
# CONFIGURATION
# ============================================================

OTP_EXPIRE_MINUTES = 10

OTP_MAX_ATTEMPTS = 5

RESET_TOKEN_EXPIRE_MINUTES = 30


# ============================================================
# COMMON HELPERS
# ============================================================

def normalize_email(email: str) -> str:
    """
    Normalize email before database operations.
    """

    return str(email).lower().strip()


def hash_value(value: str) -> str:
    """
    SHA-256 hash used for OTP/reset-token storage.
    """

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def generate_otp() -> str:
    """
    Generate a secure 6-digit OTP.
    """

    return f"{secrets.randbelow(1_000_000):06d}"


# ============================================================
# OTP CREATION
# ============================================================

def create_otp_record(
    db: Session,
    *,
    email: str,
    purpose: str,
    user_id: int | None = None,
) -> tuple[str, OTP]:
    """
    Create a new OTP.

    Previous unused OTPs for the same email/purpose
    are invalidated first.

    The transaction is NOT committed here.
    Caller commits after email delivery succeeds.
    """

    email = normalize_email(email)

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Invalidate previous unused OTPs
    # --------------------------------------------------------

    old_otps = db.scalars(
        select(OTP).where(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.verified_at.is_(None),
        )
    ).all()

    for old_otp in old_otps:
        old_otp.verified_at = now

    # --------------------------------------------------------
    # Generate new OTP
    # --------------------------------------------------------

    raw_otp = generate_otp()

    otp_hash = hash_value(raw_otp)

    expires_at = (
        now
        + timedelta(
            minutes=OTP_EXPIRE_MINUTES
        )
    )

    otp = OTP(
        user_id=user_id,
        email=email,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=expires_at,
        attempts=0,
    )

    db.add(otp)

    # Make sure SQLAlchemy assigns ID without committing.
    db.flush()

    return raw_otp, otp


# ============================================================
# OTP VERIFICATION
# ============================================================

def verify_otp(
    db: Session,
    *,
    email: str,
    otp_value: str,
    purpose: str,
) -> OTP:
    """
    Verify the latest valid OTP.
    """

    email = normalize_email(email)

    otp = db.scalar(
        select(OTP)
        .where(
            OTP.email == email,
            OTP.purpose == purpose,
            OTP.verified_at.is_(None),
        )
        .order_by(
            OTP.created_at.desc()
        )
    )

    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )

    # --------------------------------------------------------
    # Maximum attempts
    # --------------------------------------------------------

    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Too many incorrect OTP attempts. "
                "Please request a new OTP."
            ),
        )

    # --------------------------------------------------------
    # Expiry
    # --------------------------------------------------------

    now = datetime.now(timezone.utc)

    expires_at = otp.expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:

        otp.verified_at = now

        db.add(otp)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "OTP has expired. "
                "Please request a new OTP."
            ),
        )

    # --------------------------------------------------------
    # Validate OTP
    # --------------------------------------------------------

    submitted_hash = hash_value(
        str(otp_value).strip()
    )

    if not secrets.compare_digest(
        otp.otp_hash,
        submitted_hash,
    ):

        otp.attempts += 1

        db.add(otp)
        db.commit()

        remaining_attempts = max(
            0,
            OTP_MAX_ATTEMPTS - otp.attempts,
        )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid OTP. "
                f"{remaining_attempts} attempts remaining."
            ),
        )

    # --------------------------------------------------------
    # OTP verified
    # --------------------------------------------------------

    otp.verified_at = now

    db.add(otp)
    db.commit()
    db.refresh(otp)

    return otp


# ============================================================
# EMAIL OTP HELPER
# ============================================================

def send_generated_otp_email(
    *,
    email: str,
    otp: str,
    purpose: str,
) -> None:
    """
    Send generated OTP using configured SMTP server.
    """

    try:

        send_otp_email(
            to_email=email,
            otp=otp,
            purpose=purpose,
        )

    except Exception as exc:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Unable to send verification email. "
                "Please check the email service configuration "
                "and try again."
            ),
        ) from exc


# ============================================================
# RESET TOKEN HELPERS
# ============================================================

def hash_reset_token(token: str) -> str:
    """
    Hash password reset token.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_reset_token() -> tuple[
    str,
    str,
    datetime,
]:
    """
    Create a secure password reset token.
    """

    raw_token = secrets.token_urlsafe(48)

    token_hash = hash_reset_token(
        raw_token
    )

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=RESET_TOKEN_EXPIRE_MINUTES
        )
    )

    return (
        raw_token,
        token_hash,
        expires_at,
    )


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Create a new doctor account.
    """

    email = normalize_email(
        payload.email
    )

    full_name = payload.full_name.strip()

    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Full name must contain at least 2 characters.",
        )

    # --------------------------------------------------------
    # Check existing account
    # --------------------------------------------------------

    existing_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "An account with this email "
                "already exists."
            ),
        )

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user = User(
        full_name=full_name,
        email=email,
        hashed_password=hash_password(
            payload.password
        ),
        role="doctor",
        is_active=True,
    )

    db.add(user)

    try:

        db.commit()
        db.refresh(user)

    except Exception:

        db.rollback()
        raise

    return user


# ============================================================
# REGISTER - SEND OTP
# ============================================================

@router.post(
    "/register/send-otp",
)
def send_signup_otp(
    email: str,
    db: Session = Depends(get_db),
):
    """
    Send signup verification OTP.
    """

    email = normalize_email(email)

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No account was found for this email."
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    try:

        raw_otp, _ = create_otp_record(
            db,
            email=email,
            purpose="signup",
            user_id=user.id,
        )

        send_generated_otp_email(
            email=email,
            otp=raw_otp,
            purpose="signup",
        )

        db.commit()

    except HTTPException:

        db.rollback()
        raise

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Unable to send verification email. "
                "Please try again later."
            ),
        )

    return {
        "message": (
            "Signup verification OTP "
            "has been sent to your email."
        ),
        "expires_in_seconds": (
            OTP_EXPIRE_MINUTES * 60
        ),
    }


# ============================================================
# REGISTER - VERIFY OTP
# ============================================================

@router.post(
    "/register/verify-otp",
)
def verify_signup_otp(
    payload: VerifySignupOTPRequest,
    db: Session = Depends(get_db),
):
    """
    Verify signup OTP.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    verify_otp(
        db,
        email=email,
        otp_value=payload.otp,
        purpose="signup",
    )

    return {
        "message": (
            "Signup email verified successfully."
        ),
    }


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Verify email/password and send login OTP.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    # --------------------------------------------------------
    # Verify credentials
    # --------------------------------------------------------

    if not user or not verify_password(
        payload.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # --------------------------------------------------------
    # Generate + email login OTP
    # --------------------------------------------------------

    try:

        raw_otp, _ = create_otp_record(
            db,
            email=email,
            purpose="login",
            user_id=user.id,
        )

        send_generated_otp_email(
            email=email,
            otp=raw_otp,
            purpose="login",
        )

        db.commit()

    except HTTPException:

        db.rollback()
        raise

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Unable to send verification email. "
                "Please try again later."
            ),
        )

    return {
        "message": (
            "Credentials verified. "
            "A verification code has been sent "
            "to your email."
        ),
        "otp_required": True,
        "expires_in_seconds": (
            OTP_EXPIRE_MINUTES * 60
        ),
    }


# ============================================================
# LOGIN - VERIFY OTP
# ============================================================

@router.post(
    "/login/verify-otp",
    response_model=TokenResponse,
)
def verify_login_otp(
    payload: VerifyLoginOTPRequest,
    db: Session = Depends(get_db),
):
    """
    Verify login OTP and create JWT.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication request.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    otp = verify_otp(
        db,
        email=email,
        otp_value=payload.otp,
        purpose="login",
    )

    if otp.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication request.",
        )

    # --------------------------------------------------------
    # Create access token only after OTP verification
    # --------------------------------------------------------

    access_token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Return currently authenticated user.
    """

    return current_user


# ============================================================
# FORGOT PASSWORD
# ============================================================

@router.post(
    "/forgot-password",
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Generate and email password-reset OTP.

    Response does not reveal whether
    the account exists.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    # --------------------------------------------------------
    # Do not reveal account existence
    # --------------------------------------------------------

    generic_message = (
        "If an account exists for this email, "
        "a password reset OTP has been sent."
    )

    if not user or not user.is_active:
        return {
            "message": generic_message,
        }

    # --------------------------------------------------------
    # Generate + email OTP
    # --------------------------------------------------------

    try:

        raw_otp, _ = create_otp_record(
            db,
            email=email,
            purpose="forgot_password",
            user_id=user.id,
        )

        send_generated_otp_email(
            email=email,
            otp=raw_otp,
            purpose="password_reset",
        )

        db.commit()

    except HTTPException:

        db.rollback()
        raise

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Unable to send password reset email. "
                "Please try again later."
            ),
        )

    return {
        "message": generic_message,
        "otp_required": True,
        "expires_in_seconds": (
            OTP_EXPIRE_MINUTES * 60
        ),
    }


# ============================================================
# FORGOT PASSWORD - VERIFY OTP
# ============================================================

@router.post(
    "/forgot-password/verify-otp",
)
def verify_forgot_password_otp(
    payload: VerifyForgotPasswordOTPRequest,
    db: Session = Depends(get_db),
):
    """
    Verify password-reset OTP and generate
    a temporary reset token.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )

    verify_otp(
        db,
        email=email,
        otp_value=payload.otp,
        purpose="forgot_password",
    )

    # --------------------------------------------------------
    # Create reset token
    # --------------------------------------------------------

    (
        raw_token,
        token_hash,
        expires_at,
    ) = create_reset_token()

    user.reset_token_hash = token_hash
    user.reset_token_expires_at = expires_at

    try:

        db.add(user)
        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": (
            "OTP verified successfully. "
            "You can now reset your password."
        ),
        "reset_token": raw_token,
        "expires_in_minutes": (
            RESET_TOKEN_EXPIRE_MINUTES
        ),
    }


# ============================================================
# RESET PASSWORD
# ============================================================

@router.post(
    "/reset-password",
)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Reset password using reset token.
    """

    token_hash = hash_reset_token(
        payload.token
    )

    user = db.scalar(
        select(User).where(
            User.reset_token_hash == token_hash
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token."
            ),
        )

    if not user.reset_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token."
            ),
        )

    now = datetime.now(timezone.utc)

    expires_at = user.reset_token_expires_at

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:

        user.reset_token_hash = None
        user.reset_token_expires_at = None

        db.add(user)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid or expired "
                "password reset token."
            ),
        )

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    user.hashed_password = hash_password(
        payload.new_password
    )

    # --------------------------------------------------------
    # Invalidate reset token
    # --------------------------------------------------------

    user.reset_token_hash = None
    user.reset_token_expires_at = None

    try:

        db.add(user)
        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": (
            "Password reset successfully. "
            "You can now log in."
        ),
    }


# ============================================================
# RESET PASSWORD WITH OTP
# ============================================================

@router.post(
    "/reset-password-with-otp",
)
def reset_password_with_otp(
    payload: ResetPasswordWithOTPRequest,
    db: Session = Depends(get_db),
):
    """
    Reset password directly using OTP.
    """

    email = normalize_email(
        payload.email
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP.",
        )

    verify_otp(
        db,
        email=email,
        otp_value=payload.otp,
        purpose="forgot_password",
    )

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    user.hashed_password = hash_password(
        payload.new_password
    )

    # --------------------------------------------------------
    # Invalidate reset token
    # --------------------------------------------------------

    user.reset_token_hash = None
    user.reset_token_expires_at = None

    try:

        db.add(user)
        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": (
            "Password reset successfully. "
            "You can now log in."
        ),
    }


# ============================================================
# CHANGE PASSWORD
# ============================================================

@router.post(
    "/change-password",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    """
    Change password for authenticated user.
    """

    # --------------------------------------------------------
    # Verify current password
    # --------------------------------------------------------

    if not verify_password(
        payload.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # --------------------------------------------------------
    # Prevent same password
    # --------------------------------------------------------

    if verify_password(
        payload.new_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "New password must be different "
                "from the current password"
            ),
        )

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    current_user.hashed_password = hash_password(
        payload.new_password
    )

    # --------------------------------------------------------
    # Invalidate password reset token
    # --------------------------------------------------------

    current_user.reset_token_hash = None
    current_user.reset_token_expires_at = None

    try:

        db.add(current_user)
        db.commit()

    except Exception:

        db.rollback()
        raise

    return {
        "message": (
            "Password changed successfully."
        ),
    }