import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


# ============================================================
# RESET TOKEN CONFIG
# ============================================================

RESET_TOKEN_EXPIRE_MINUTES = 30


# ============================================================
# RESET TOKEN HELPERS
# ============================================================

def hash_reset_token(token: str) -> str:
    """
    Hash the raw reset token before storing it in PostgreSQL.
    """

    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_reset_token() -> tuple[str, str, datetime]:
    """
    Create a secure random password-reset token.

    Returns:
        raw_token
        token_hash
        expires_at
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
    email = str(
        payload.email
    ).lower().strip()

    existing_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        hashed_password=hash_password(
            payload.password
        ),
        role="doctor",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login_user(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    email = str(
        payload.email
    ).lower().strip()

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

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

    access_token = create_access_token(
        str(user.id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ============================================================
# CURRENT LOGGED-IN USER
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
    email = str(
        payload.email
    ).lower().strip()

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    # IMPORTANT:
    # Don't reveal whether an email exists.
    if not user:
        return {
            "message": (
                "If an account exists for this email, "
                "password reset instructions have been generated."
            )
        }

    if not user.is_active:
        return {
            "message": (
                "If an account exists for this email, "
                "password reset instructions have been generated."
            )
        }

    raw_token, token_hash, expires_at = (
        create_reset_token()
    )

    user.reset_token_hash = token_hash
    user.reset_token_expires_at = expires_at

    db.add(user)
    db.commit()

    # ========================================================
    # DEVELOPMENT RESPONSE
    # ========================================================
    #
    # DO NOT expose this token in production.
    #
    # Later we will send:
    #
    # https://your-frontend/reset-password?token=...
    #
    # through email.
    #

    return {
        "message": (
            "If an account exists for this email, "
            "password reset instructions have been generated."
        ),
        "development_token": raw_token,
        "expires_in_minutes": RESET_TOKEN_EXPIRE_MINUTES,
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
    token_hash = hash_reset_token(
        payload.token
    )

    user = db.scalar(
        select(User).where(
            User.reset_token_hash
            == token_hash
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    if not user.reset_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    now = datetime.now(timezone.utc)

    expires_at = user.reset_token_expires_at

    # Handle timezone-naive values safely.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    if expires_at <= now:
        # Remove expired token.
        user.reset_token_hash = None
        user.reset_token_expires_at = None

        db.add(user)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token",
        )

    # ========================================================
    # UPDATE PASSWORD
    # ========================================================

    user.hashed_password = hash_password(
        payload.new_password
    )

    # Token becomes invalid immediately.
    user.reset_token_hash = None
    user.reset_token_expires_at = None

    db.add(user)
    db.commit()

    return {
        "message": "Password reset successfully. You can now log in."
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
    # ========================================================
    # VERIFY CURRENT PASSWORD
    # ========================================================

    if not verify_password(
        payload.current_password,
        current_user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # ========================================================
    # PREVENT SAME PASSWORD
    # ========================================================

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

    # ========================================================
    # UPDATE PASSWORD
    # ========================================================

    current_user.hashed_password = hash_password(
        payload.new_password
    )

    # Invalidate any pending password-reset token.
    current_user.reset_token_hash = None
    current_user.reset_token_expires_at = None

    db.add(current_user)
    db.commit()

    return {
        "message": "Password changed successfully."
    }