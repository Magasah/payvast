"""Shared FastAPI dependencies: DB session, current user, admin guard."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import User, UserRole
from app.security import TokenError, decode_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="not_authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise _UNAUTHORIZED
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (TokenError, ValueError) as exc:
        raise _UNAUTHORIZED from exc
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise _UNAUTHORIZED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def is_admin(user: User) -> bool:
    """Admin = role admin AND a Telegram id from ADMIN_TELEGRAM_IDS AND an active account.

    The role alone is never enough: even a row edited by hand in the DB, or an old email
    admin, gets no access unless its Telegram id is in the env list.
    """
    return (
        user.is_active
        and user.role == UserRole.ADMIN
        and user.telegram_id is not None
        and user.telegram_id in get_settings().admin_ids
    )


async def require_admin(user: CurrentUser) -> User:
    if not is_admin(user):
        # 404, not 403: the admin area does not reveal that it exists.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
