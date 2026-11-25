"""Money-critical operations. Read this before changing anything here.

confirm_payment runs in ONE transaction:
  1. SELECT payment FOR UPDATE      -> parallel confirms of the same payment queue up here
  2. check status == pending_review -> the 2nd, 3rd... confirm sees `confirmed` and stops
  3. SELECT user FOR UPDATE         -> two different payments of one user extend in order
  4. extend (or create) the subscription, call the panel with the ABSOLUTE new expiry
  5. mark payment confirmed, write admin_audit_log, COMMIT
Any error before COMMIT rolls back everything, including the audit entry.
Lock order is always payment -> user -> subscription, so there are no deadlocks.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, PaymentStatus, Server, Subscription, SubscriptionStatus, User
from app.panel import PanelAdapter, PanelError
from app.services.audit import audit
from app.services.servers import pick_server


class BillingError(Exception):
    def __init__(self, code: str, http_status: int) -> None:
        super().__init__(code)
        self.code = code
        self.http_status = http_status


NOT_FOUND = ("not_found", 404)
ALREADY_CONFIRMED = ("already_confirmed", 409)
NOT_REVIEWABLE = ("payment_not_reviewable", 409)
NO_SERVER = ("no_server_available", 503)
PANEL_FAILED = ("panel_error", 502)


async def _lock_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment:
    payment = (
        await session.scalars(select(Payment).where(Payment.id == payment_id).with_for_update())
    ).first()
    if payment is None:
        raise BillingError(*NOT_FOUND)
    return payment


async def confirm_payment(
    session: AsyncSession, payment_id: uuid.UUID, admin: User, panel: PanelAdapter
) -> Payment:
    try:
        payment = await _lock_payment(session, payment_id)
        if payment.status == PaymentStatus.CONFIRMED:
            raise BillingError(*ALREADY_CONFIRMED)
        if payment.status != PaymentStatus.PENDING_REVIEW:
            raise BillingError(*NOT_REVIEWABLE)

        await session.execute(select(User.id).where(User.id == payment.user_id).with_for_update())
        sub = (
            await session.scalars(
                select(Subscription)
                .where(Subscription.user_id == payment.user_id)
                .with_for_update(of=Subscription)
            )
        ).first()

        now = datetime.now(UTC)
        base = max(sub.expires_at, now) if sub is not None else now
        new_expiry = base + timedelta(days=payment.duration_days)

        try:
            if sub is None:
                sub = await _create_subscription(session, payment, new_expiry, panel)
            else:
                await _extend_subscription(session, sub, payment, new_expiry, panel)
        except PanelError as exc:
            raise BillingError(*PANEL_FAILED) from exc

        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_at = now
        payment.reviewed_at = now
        payment.reviewed_by = admin.id
        audit(
            session,
            admin,
            "payment.confirm",
            "payment",
            payment.id,
            amount_dirams=payment.amount_dirams,
            subscription_id=str(sub.id),
            new_expires_at=new_expiry.isoformat(),
        )
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    await session.refresh(payment)
    return payment


async def _create_subscription(
    session: AsyncSession, payment: Payment, expires_at: datetime, panel: PanelAdapter
) -> Subscription:
    server = await pick_server(session)
    if server is None:
        raise BillingError(*NO_SERVER)
    client_id = str(uuid.uuid4())
    created = await panel.create_client(server, client_id, payment.device_limit, expires_at)
    sub = Subscription(
        user_id=payment.user_id,
        server_id=server.id,
        panel_client_id=client_id,
        subscription_url=created.subscription_url,
        device_limit=payment.device_limit,
        status=SubscriptionStatus.ACTIVE,
        expires_at=expires_at,
    )
    session.add(sub)
    await session.flush()
    return sub


async def _extend_subscription(
    session: AsyncSession,
    sub: Subscription,
    payment: Payment,
    expires_at: datetime,
    panel: PanelAdapter,
) -> None:
    server = await session.get(Server, sub.server_id) if sub.server_id is not None else None
    if server is None or not server.is_active:
        server = await pick_server(session)
        if server is None:
            raise BillingError(*NO_SERVER)
        created = await panel.create_client(
            server, sub.panel_client_id, payment.device_limit, expires_at
        )
        sub.server_id = server.id
        sub.subscription_url = created.subscription_url
    else:
        await panel.extend_client(server, sub.panel_client_id, payment.device_limit, expires_at)
    sub.expires_at = expires_at
    sub.device_limit = max(sub.device_limit, payment.device_limit)
    sub.status = SubscriptionStatus.ACTIVE


async def reject_payment(
    session: AsyncSession, payment_id: uuid.UUID, admin: User, reason: str
) -> Payment:
    try:
        payment = await _lock_payment(session, payment_id)
        if payment.status == PaymentStatus.CONFIRMED:
            raise BillingError(*ALREADY_CONFIRMED)
        if payment.status == PaymentStatus.REJECTED:
            raise BillingError(*NOT_REVIEWABLE)
        now = datetime.now(UTC)
        payment.status = PaymentStatus.REJECTED
        payment.reject_reason = reason
        payment.reviewed_at = now
        payment.reviewed_by = admin.id
        audit(session, admin, "payment.reject", "payment", payment.id, reason=reason)
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    await session.refresh(payment)
    return payment


async def move_subscription(
    session: AsyncSession,
    subscription_id: uuid.UUID,
    admin: User,
    panel: PanelAdapter,
    target_server_id: int | None,
) -> Subscription:
    """Move a user to another server (e.g. the current IP got blocked)."""
    try:
        sub = (
            await session.scalars(
                select(Subscription)
                .where(Subscription.id == subscription_id)
                .with_for_update(of=Subscription)
            )
        ).first()
        if sub is None:
            raise BillingError(*NOT_FOUND)
        old_server = await session.get(Server, sub.server_id) if sub.server_id else None
        if target_server_id is not None:
            target = await session.get(Server, target_server_id)
            if target is None or not target.is_active or target.is_blocked:
                raise BillingError(*NO_SERVER)
        else:
            target = await pick_server(session, exclude_id=sub.server_id)
            if target is None:
                raise BillingError(*NO_SERVER)
        try:
            created = await panel.create_client(
                target, sub.panel_client_id, sub.device_limit, sub.expires_at
            )
            if old_server is not None and old_server.id != target.id:
                await panel.disable_client(old_server, sub.panel_client_id)
        except PanelError as exc:
            raise BillingError(*PANEL_FAILED) from exc
        audit(
            session,
            admin,
            "subscription.move",
            "subscription",
            sub.id,
            from_server=old_server.id if old_server else None,
            to_server=target.id,
        )
        sub.server_id = target.id
        sub.subscription_url = created.subscription_url
        await session.commit()
    except BaseException:
        await session.rollback()
        raise
    await session.refresh(sub)
    return sub
