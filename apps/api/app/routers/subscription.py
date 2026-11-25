"""The current user's subscription: link, expiry and QR code."""

import io
from datetime import UTC, datetime

import qrcode
import qrcode.image.svg
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.deps import CurrentUser, SessionDep
from app.models import Subscription, SubscriptionStatus

router = APIRouter(prefix="/api/subscription", tags=["subscription"])

NO_STORE = {"Cache-Control": "no-store"}


class SubscriptionOut(BaseModel):
    id: str
    status: SubscriptionStatus
    expires_at: datetime
    days_left: int
    device_limit: int
    subscription_url: str | None


def _effective_status(sub: Subscription) -> SubscriptionStatus:
    if sub.status == SubscriptionStatus.ACTIVE and sub.expires_at <= datetime.now(UTC):
        return SubscriptionStatus.EXPIRED
    return sub.status


def subscription_out(sub: Subscription) -> SubscriptionOut:
    state = _effective_status(sub)
    seconds = (sub.expires_at - datetime.now(UTC)).total_seconds()
    return SubscriptionOut(
        id=str(sub.id),
        status=state,
        expires_at=sub.expires_at,
        days_left=max(0, int(seconds // 86400)),
        device_limit=sub.device_limit,
        # The link is only handed out while the subscription is usable.
        subscription_url=sub.subscription_url if state == SubscriptionStatus.ACTIVE else None,
    )


async def _my_subscription(user: CurrentUser, session: SessionDep) -> Subscription:
    sub = (
        await session.scalars(select(Subscription).where(Subscription.user_id == user.id))
    ).first()
    if sub is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no_subscription")
    return sub


@router.get("", response_model=SubscriptionOut)
async def my_subscription(
    user: CurrentUser, session: SessionDep, response: Response
) -> SubscriptionOut:
    response.headers.update(NO_STORE)
    return subscription_out(await _my_subscription(user, session))


@router.get("/qr", response_class=Response)
async def my_subscription_qr(user: CurrentUser, session: SessionDep) -> Response:
    out = subscription_out(await _my_subscription(user, session))
    if out.subscription_url is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="subscription_inactive")
    img = qrcode.make(
        out.subscription_url,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    buf = io.BytesIO()
    img.save(buf)
    return Response(content=buf.getvalue(), media_type="image/svg+xml", headers=NO_STORE)
