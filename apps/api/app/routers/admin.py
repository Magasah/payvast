"""Admin endpoints. Every route requires an admin (role + Telegram id from .env, see deps).

Every state change and every receipt view is written to admin_audit_log.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.deps import AdminUser, SessionDep, is_admin, require_admin
from app.models import (
    AdminAuditLog,
    Payment,
    PaymentStatus,
    Plan,
    Server,
    Subscription,
    SubscriptionStatus,
    User,
)
from app.panel import PanelAdapter, get_panel
from app.routers.payments import to_out
from app.routers.subscription import SubscriptionOut, subscription_out
from app.schemas.admin import (
    AdjustDaysIn,
    AdminPaymentOut,
    AdminSubscriptionOut,
    AdminUserDetail,
    AdminUserPage,
    AdminUserRow,
    AuditOut,
    AuditPage,
    MoveIn,
    NoteIn,
    RejectIn,
    ServerIn,
    ServerOut,
    ServerPatch,
    UserActiveIn,
)
from app.schemas.payment import PaymentOut
from app.services import billing
from app.services.audit import audit
from app.services.receipts import receipt_path
from app.telegram.notify import notify_user_confirmed, notify_user_rejected
from app.utils import format_date

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

PanelDep = Annotated[PanelAdapter, Depends(get_panel)]


def _raise(exc: billing.BillingError) -> HTTPException:
    return HTTPException(exc.http_status, detail=exc.code)


def _payment_row(p: Payment, user: User, plan_code: str) -> AdminPaymentOut:
    return AdminPaymentOut(
        id=p.id,
        user_id=user.id,
        user_email=user.email,
        user_telegram=user.telegram_username,
        plan_code=plan_code,
        method=p.method,
        amount_dirams=p.amount_dirams,
        duration_days=p.duration_days,
        status=p.status,
        has_receipt=p.receipt_file is not None,
        created_at=p.created_at,
        reviewed_at=p.reviewed_at,
        reject_reason=p.reject_reason,
    )


@router.get("/payments", response_model=list[AdminPaymentOut])
async def list_payments(
    session: SessionDep,
    status_filter: Annotated[PaymentStatus, Query(alias="status")] = PaymentStatus.PENDING_REVIEW,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AdminPaymentOut]:
    order = (
        Payment.created_at
        if status_filter in (PaymentStatus.PENDING_REVIEW, PaymentStatus.AWAITING_RECEIPT)
        else Payment.created_at.desc()
    )
    rows = await session.execute(
        select(Payment, User, Plan.code)
        .join(User, User.id == Payment.user_id)
        .join(Plan, Plan.id == Payment.plan_id)
        .where(Payment.status == status_filter)
        .order_by(order)
        .limit(limit)
    )
    return [_payment_row(p, u, code) for p, u, code in rows.tuples()]


@router.get("/payments/{payment_id}/receipt")
async def get_receipt(payment_id: uuid.UUID, admin: AdminUser, session: SessionDep) -> FileResponse:
    payment = await session.get(Payment, payment_id)
    if payment is None or payment.receipt_file is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    path = receipt_path(payment.receipt_file)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    audit(session, admin, "payment.view_receipt", "payment", payment.id)
    await session.commit()
    media = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[path.suffix[1:]]
    return FileResponse(
        path,
        media_type=media,
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'none'",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.post("/payments/{payment_id}/confirm", response_model=PaymentOut)
async def confirm(
    payment_id: uuid.UUID,
    admin: AdminUser,
    session: SessionDep,
    panel: PanelDep,
    background: BackgroundTasks,
) -> PaymentOut:
    try:
        payment = await billing.confirm_payment(session, payment_id, admin, panel)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    owner = await session.get(User, payment.user_id)
    sub = (
        await session.scalars(select(Subscription).where(Subscription.user_id == payment.user_id))
    ).first()
    if owner is not None and owner.telegram_id and sub is not None:
        background.add_task(
            notify_user_confirmed, owner.telegram_id, owner.locale, format_date(sub.expires_at)
        )
    return to_out(payment)


@router.post("/payments/{payment_id}/reject", response_model=PaymentOut)
async def reject(
    payment_id: uuid.UUID,
    body: RejectIn,
    admin: AdminUser,
    session: SessionDep,
    background: BackgroundTasks,
) -> PaymentOut:
    try:
        payment = await billing.reject_payment(session, payment_id, admin, body.reason)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    owner = await session.get(User, payment.user_id)
    if owner is not None and owner.telegram_id:
        background.add_task(notify_user_rejected, owner.telegram_id, owner.locale, body.reason)
    return to_out(payment)


@router.get("/servers", response_model=list[ServerOut])
async def list_servers(session: SessionDep) -> list[ServerOut]:
    rows = await session.scalars(select(Server).order_by(Server.id))
    return [ServerOut.model_validate(s) for s in rows]


@router.post("/servers", response_model=ServerOut, status_code=status.HTTP_201_CREATED)
async def create_server(body: ServerIn, admin: AdminUser, session: SessionDep) -> ServerOut:
    server = Server(**body.model_dump())
    session.add(server)
    try:
        await session.flush()
        audit(session, admin, "server.create", "server", server.id, **body.model_dump())
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="server_exists") from exc
    return ServerOut.model_validate(server)


@router.patch("/servers/{server_id}", response_model=ServerOut)
async def update_server(
    server_id: int, body: ServerPatch, admin: AdminUser, session: SessionDep
) -> ServerOut:
    server = await session.get(Server, server_id, with_for_update=True)
    if server is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(server, field, value)
    audit(session, admin, "server.update", "server", server.id, **changes)
    await session.commit()
    return ServerOut.model_validate(server)


@router.post("/subscriptions/{subscription_id}/move", response_model=SubscriptionOut)
async def move(
    subscription_id: uuid.UUID,
    body: MoveIn,
    admin: AdminUser,
    session: SessionDep,
    panel: PanelDep,
) -> SubscriptionOut:
    try:
        sub = await billing.move_subscription(
            session, subscription_id, admin, panel, body.server_id
        )
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    return subscription_out(sub)


# --- Users and subscription terms ---------------------------------------------------------


def _sub_out(sub: Subscription) -> AdminSubscriptionOut:
    now = datetime.now(UTC)
    state = sub.status
    if state == SubscriptionStatus.ACTIVE and sub.expires_at <= now:
        state = SubscriptionStatus.EXPIRED
    return AdminSubscriptionOut(
        id=sub.id,
        status=state,
        expires_at=sub.expires_at,
        days_left=max(0, int((sub.expires_at - now).total_seconds() // 86400)),
        device_limit=sub.device_limit,
        server_id=sub.server_id,
        subscription_url=sub.subscription_url,
    )


def _user_row(user: User, sub: Subscription | None) -> AdminUserRow:
    sub_out = _sub_out(sub) if sub else None
    return AdminUserRow(
        id=user.id,
        email=user.email,
        telegram_id=user.telegram_id,
        telegram_username=user.telegram_username,
        is_admin=is_admin(user),
        is_active=user.is_active,
        locale=user.locale,
        created_at=user.created_at,
        subscription_status=sub_out.status if sub_out else None,
        expires_at=sub_out.expires_at if sub_out else None,
    )


@router.get("/users", response_model=AdminUserPage)
async def list_users(
    session: SessionDep,
    q: Annotated[str, Query(max_length=64)] = "",
    sub_status: Annotated[SubscriptionStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> AdminUserPage:
    stmt = select(User, Subscription).outerjoin(Subscription, Subscription.user_id == User.id)
    term = q.strip().lstrip("@")
    if term:
        # Bound parameter with escaped wildcards: no SQL injection, no LIKE tricks.
        like = "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        stmt = stmt.where(
            or_(
                User.email.ilike(like, escape="\\"),
                User.telegram_username.ilike(like, escape="\\"),
                cast(User.telegram_id, String).like(like, escape="\\"),
            )
        )
    if sub_status is not None:
        now = datetime.now(UTC)
        if sub_status == SubscriptionStatus.EXPIRED:
            stmt = stmt.where(
                or_(
                    Subscription.status == SubscriptionStatus.EXPIRED,
                    (Subscription.status == SubscriptionStatus.ACTIVE)
                    & (Subscription.expires_at <= now),
                )
            )
        elif sub_status == SubscriptionStatus.ACTIVE:
            stmt = stmt.where(
                Subscription.status == SubscriptionStatus.ACTIVE, Subscription.expires_at > now
            )
        else:
            stmt = stmt.where(Subscription.status == sub_status)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.execute(
        stmt.order_by(User.created_at.desc(), User.id).limit(limit).offset(offset)
    )
    return AdminUserPage(items=[_user_row(u, sub) for u, sub in rows.tuples()], total=total or 0)


async def _detail(session: SessionDep, user_id: uuid.UUID) -> AdminUserDetail:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    sub = (
        await session.scalars(select(Subscription).where(Subscription.user_id == user_id))
    ).first()
    rows = await session.execute(
        select(Payment, Plan.code)
        .join(Plan, Plan.id == Payment.plan_id)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(50)
    )
    return AdminUserDetail(
        user=_user_row(user, sub),
        subscription=_sub_out(sub) if sub else None,
        payments=[_payment_row(p, user, code) for p, code in rows.tuples()],
    )


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def user_detail(user_id: uuid.UUID, session: SessionDep) -> AdminUserDetail:
    return await _detail(session, user_id)


@router.post("/users/{user_id}/subscription/days", response_model=AdminUserDetail)
async def adjust_days(
    user_id: uuid.UUID, body: AdjustDaysIn, admin: AdminUser, session: SessionDep, panel: PanelDep
) -> AdminUserDetail:
    try:
        await billing.adjust_days(
            session, user_id, admin, panel, body.days, body.device_limit, body.note
        )
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    return await _detail(session, user_id)


@router.post("/users/{user_id}/subscription/revoke", response_model=AdminUserDetail)
async def revoke(
    user_id: uuid.UUID, body: NoteIn, admin: AdminUser, session: SessionDep, panel: PanelDep
) -> AdminUserDetail:
    try:
        await billing.revoke(session, user_id, admin, panel, body.note)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    return await _detail(session, user_id)


@router.post("/users/{user_id}/subscription/restore", response_model=AdminUserDetail)
async def restore(
    user_id: uuid.UUID, admin: AdminUser, session: SessionDep, panel: PanelDep
) -> AdminUserDetail:
    try:
        await billing.restore(session, user_id, admin, panel)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    return await _detail(session, user_id)


@router.post("/users/{user_id}/active", response_model=AdminUserDetail)
async def set_active(
    user_id: uuid.UUID, body: UserActiveIn, admin: AdminUser, session: SessionDep
) -> AdminUserDetail:
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if user.id == admin.id:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="cannot_block_self")
    user.is_active = body.is_active
    if not body.is_active:
        user.token_version += 1  # log the blocked account out everywhere
    audit(session, admin, "user.unblock" if body.is_active else "user.block", "user", user.id)
    await session.commit()
    return await _detail(session, user_id)


@router.get("/audit", response_model=AuditPage)
async def audit_log(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: Annotated[int | None, Query(gt=0)] = None,
    target_id: Annotated[str | None, Query(max_length=64)] = None,
) -> AuditPage:
    stmt = (
        select(AdminAuditLog, User.telegram_username, User.telegram_id)
        .outerjoin(User, User.id == AdminAuditLog.admin_id)
        .order_by(AdminAuditLog.id.desc())
        .limit(limit + 1)
    )
    if before is not None:
        stmt = stmt.where(AdminAuditLog.id < before)
    if target_id:
        stmt = stmt.where(AdminAuditLog.target_id == target_id)
    rows = list((await session.execute(stmt)).tuples())
    more = len(rows) > limit
    rows = rows[:limit]
    items = [
        AuditOut(
            id=e.id,
            created_at=e.created_at,
            admin=f"@{uname}" if uname else (str(tid) if tid else None),
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            details=e.details,
        )
        for e, uname, tid in rows
    ]
    return AuditPage(items=items, next_before=items[-1].id if more and items else None)
