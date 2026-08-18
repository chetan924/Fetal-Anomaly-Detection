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