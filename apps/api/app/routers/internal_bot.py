"""Endpoints for the Telegram bot only (same docker network).

Protected by the BOT_API_SECRET header. The Next.js proxy never forwards /api/internal/*,
so browsers cannot reach these at all. Empty secret = endpoints answer 404.
"""

import hmac
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.config import get_settings
from app.deps import SessionDep, is_admin
from app.models import Payment, PaymentStatus, Subscription, SubscriptionStatus, User
from app.routers.subscription import subscription_out
from app.services.users import UpsertConflict, upsert_telegram_user


async def require_bot(x_bot_secret: Annotated[str, Header()] = "") -> None:
    expected = get_settings().bot_api_secret.get_secret_value()
    if not expected or not hmac.compare_digest(x_bot_secret.encode(), expected.encode()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")


router = APIRouter(
    prefix="/api/internal/bot",
    tags=["internal"],
    dependencies=[Depends(require_bot)],
    include_in_schema=False,
)


class BotUserIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, max_length=32)
    language_code: str | None = Field(default=None, max_length=8)
    locale: Literal["tg", "ru"] | None = None


class BotProfileOut(BaseModel):
    locale: str
    is_admin: bool
    has_email: bool
    subscription_status: SubscriptionStatus | None
    expires_at: datetime | None
    days_left: int | None
    device_limit: int | None
    pending_payments: int


async def _profile(session: SessionDep, user: User) -> BotProfileOut:
    sub = (
        await session.scalars(select(Subscription).where(Subscription.user_id == user.id))
    ).first()
    out = subscription_out(sub) if sub else None
    pending = len(
        (
            await session.scalars(
                select(Payment.id).where(
                    Payment.user_id == user.id, Payment.status == PaymentStatus.PENDING_REVIEW
                )
            )
        ).all()
    )
    return BotProfileOut(
        locale=user.locale,
        is_admin=is_admin(user),
        has_email=user.email is not None,
        subscription_status=out.status if out else None,
        expires_at=out.expires_at if out else None,
        days_left=out.days_left if out else None,
        device_limit=out.device_limit if out else None,
        pending_payments=pending,
    )


@router.put("/users/{telegram_id}", response_model=BotProfileOut)
async def upsert_user(telegram_id: int, body: BotUserIn, session: SessionDep) -> BotProfileOut:
    if telegram_id <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="bad_telegram_id")
    try:
        user = await upsert_telegram_user(
            session, telegram_id, body.username, body.language_code, body.locale
        )
    except UpsertConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="try_again") from exc
    return await _profile(session, user)
