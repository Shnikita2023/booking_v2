"""Password hashing and JWT issuance/verification."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from booking.core.config import get_settings

_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, ValueError):
        return False


def create_token(
    token_type: TokenType,
    subject: str,
    *,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Create a signed JWT. Returns (token, expires_at)."""
    settings = get_settings()
    ttl = (
        timedelta(minutes=settings.access_ttl_min)
        if token_type == "access"
        else timedelta(days=settings.refresh_ttl_days)
    )
    now = datetime.now(UTC)
    expires_at = now + ttl
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, expires_at


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload
