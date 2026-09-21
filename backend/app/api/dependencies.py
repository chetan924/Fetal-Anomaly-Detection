from typing import Optional
from fastapi import (
    Depends,
    HTTPException,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from jwt import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import (
    decode_access_token,
)
from app.db.database import get_db
from app.models.user import User


# =========================================================
# AUTHENTICATION SCHEME
# =========================================================

bearer_scheme = HTTPBearer(
    auto_error=True,
)


# =========================================================
# CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Validate the Bearer access token and return
    the currently authenticated active user.
    """

    # -----------------------------------------------------
    # BASIC TOKEN VALIDATION
    # -----------------------------------------------------

    token = (
        credentials.credentials
        if credentials
        else ""
    ).strip()


    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    # -----------------------------------------------------
    # DECODE + VALIDATE JWT
    # -----------------------------------------------------

    try:

        payload = decode_access_token(
            token
        )

    except (
        InvalidTokenError,
        KeyError,
        TypeError,
        ValueError,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    # -----------------------------------------------------
    # USER ID
    # -----------------------------------------------------

    subject = payload.get(
        "sub"
    )


    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has no subject",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    try:

        user_id = int(
            subject
        )

    except (
        TypeError,
        ValueError,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication subject",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication subject",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    # -----------------------------------------------------
    # DATABASE USER
    # -----------------------------------------------------

    user = db.get(
        User,
        user_id,
    )


    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    # -----------------------------------------------------
    # ACTIVE ACCOUNT CHECK
    # -----------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is unavailable",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    return user

# =========================================================
# OPTIONAL AUTHENTICATION SCHEME & CURRENT USER
# =========================================================

optional_bearer_scheme = HTTPBearer(
    auto_error=False,
)

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        optional_bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    If a Bearer token is provided, validate it and return the User.
    If no token is provided, return None without raising an 401 error.
    """
    if credentials is None or not credentials.credentials:
        return None

    token = credentials.credentials.strip()
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except Exception:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    if user_id <= 0:
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None

    return user
