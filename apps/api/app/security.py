"""Password hashing (argon2) and JWT helpers."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import get_settings

TokenType = Literal["access", "refresh"]

_hasher = PasswordHasher()
# Used when the user does not exist, so login timing does not reveal registered emails.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing")


class TokenError(Exception):
    """Token is missing, expired, malformed or of the wrong type."""


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def _encode(claims: dict[str, Any], ttl: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {**claims, "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex}
    return jwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    ttl = timedelta(minutes=get_settings().jwt_access_ttl_minutes)
    return _encode({"sub": str(user_id), "role": role, "typ": "access"}, ttl)


def create_refresh_token(user_id: uuid.UUID, token_version: int) -> str:
    ttl = timedelta(days=get_settings().jwt_refresh_ttl_days)
    return _encode({"sub": str(user_id), "ver": token_version, "typ": "refresh"}, ttl)


def decode_token(token: str, expected: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],  # pinned: no "none", no algorithm confusion
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload.get("typ") != expected:
        raise TokenError("wrong token type")
    return payload
