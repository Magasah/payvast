"""Telegram user upsert, shared by WebApp login and the bot.

The role is recomputed from ADMIN_TELEGRAM_IDS on every call: being in the env list is the
only way to become admin, and removing an id from it takes the role away on the next visit.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import User, UserRole


class UpsertConflict(Exception):
    pass


async def upsert_telegram_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None,
    language_code: str | None = None,
    locale: str | None = None,
) -> User:
    role = UserRole.ADMIN if telegram_id in get_settings().admin_ids else UserRole.USER
    for _ in range(2):
        user = (
            await session.scalars(
                select(User).where(User.telegram_id == telegram_id).with_for_update()
            )
        ).first()
        if user is None:
            initial = locale or ("ru" if (language_code or "").startswith("ru") else "tg")
            user = User(
                telegram_id=telegram_id, telegram_username=username, locale=initial, role=role
            )
            session.add(user)
        else:
            if user.role != role:
                user.token_version += 1  # role changed: drop old sessions
            user.role = role
            user.telegram_username = username
            if locale:
                user.locale = locale
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()  # a parallel first visit created the row: read it again
            continue
        await session.refresh(user)
        return user
    raise UpsertConflict
