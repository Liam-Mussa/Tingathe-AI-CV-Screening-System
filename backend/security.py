"""Password hashing and token issuing.

Passwords are hashed with bcrypt; tokens are signed JWTs carrying the user id
and role. The signing key and lifetime come from the environment so production
deployments can set their own.
"""
import os
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from config import SECRET_KEY, TOKEN_TTL_HOURS


def _bcrypt_input(plain: str) -> bytes:
    """Create a fixed-length bcrypt input for any Unicode password.

    Bcrypt only accepts 72 input bytes. Hashing first avoids silent truncation
    and also keeps behavior consistent across bcrypt package versions.
    """
    return hashlib.sha256(plain.encode("utf-8")).hexdigest().encode("ascii")


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_bcrypt_input(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_input(plain), hashed.encode("ascii"))
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    """Issue a signed token that expires after the configured number of hours."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any] | None:
    """Return the token's claims, or None if it is invalid or expired."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None
