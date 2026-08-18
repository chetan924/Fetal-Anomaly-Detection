from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)


# =========================================================
# PASSWORD HASHING
# =========================================================

password_hash = PasswordHash.recommended()


# =========================================================
# PASSWORD
# =========================================================

def hash_password(
    password: str,
) -> str:
    """
    Hash a plaintext password using pwdlib's
    recommended password-hashing configuration.
    """

    if not isinstance(
        password,
        str,
    ):
        raise TypeError(
            "Password must be a string."
        )


    if not password:
        raise ValueError(
            "Password must not be empty."
        )


    return password_hash.hash(
        password
    )


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Safely verify a plaintext password against
    a stored password hash.
    """

    if not isinstance(
        plain_password,
        str,
    ):
        return False


    if not isinstance(
        hashed_password,
        str,
    ):
        return False


    if not plain_password or not hashed_password:
        return False


    try:

        return password_hash.verify(
            plain_password,
            hashed_password,
        )

    except Exception:
        # Authentication should fail closed if a stored
        # password hash is malformed or unsupported.
        return False


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(
    subject: str,
) -> str:
    """
    Create a short-lived JWT access token.

    The token contains:
      - sub: authenticated user identifier
      - iat: issued-at timestamp
      - exp: expiration timestamp

    JWT_SECRET_KEY and JWT_ALGORITHM come only from
    application configuration/environment variables.
    """

    if not isinstance(
        subject,
        str,
    ):
        raise TypeError(
            "JWT subject must be a string."
        )


    subject = subject.strip()


    if not subject:
        raise ValueError(
            "JWT subject must not be empty."
        )


    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )


    now = datetime.now(
        timezone.utc
    )


    expires_at = (
        now
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
    }


    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# =========================================================
# DECODE ACCESS TOKEN
# =========================================================

def decode_access_token(
    token: str,
) -> dict:
    """
    Decode and cryptographically validate a JWT.

    PyJWT validates the exp claim by default. Invalid,
    expired, malformed or incorrectly signed tokens raise
    InvalidTokenError and are handled by the authentication
    dependency.
    """

    if not isinstance(
        token,
        str,
    ):
        raise InvalidTokenError(
            "Token must be a string."
        )


    token = token.strip()


    if not token:
        raise InvalidTokenError(
            "Token is empty."
        )


    if not JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is not configured."
        )


    payload = jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[
            JWT_ALGORITHM,
        ],
        options={
            "require": [
                "sub",
                "iat",
                "exp",
            ],
        },
    )


    if not isinstance(
        payload,
        dict,
    ):
        raise InvalidTokenError(
            "Invalid token payload."
        )


    subject = payload.get(
        "sub"
    )


    if not isinstance(
        subject,
        str,
    ) or not subject.strip():
        raise InvalidTokenError(
            "Invalid token subject."
        )


    return payload