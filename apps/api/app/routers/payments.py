"""User side of payments: methods, create (idempotent), list, upload receipt."""

import re
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models import Payment, PaymentStatus, Plan
from app.payments import get_payment_provider
from app.ratelimit import limiter
from app.schemas.payment import BankLinkOut, PaymentCreateIn, PaymentMethodOut, PaymentOut
from app.services.receipts import delete_receipt, save_receipt
from app.telegram.notify import notify_admins_new_receipt
from app.utils import format_tjs

router = APIRouter(prefix="/api/payments", tags=["payments"])
settings = get_settings()

IDEMPOTENCY_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
MAX_OPEN_PAYMENTS = 3
OPEN_STATUSES = (PaymentStatus.AWAITING_RECEIPT, PaymentStatus.PENDING_REVIEW)


def to_out(p: Payment) -> PaymentOut:
    return PaymentOut(
        id=p.id,
        plan_id=p.plan_id,
        method=p.method,
        amount_dirams=p.amount_dirams,
        duration_days=p.duration_days,
        status=p.status,
        has_receipt=p.receipt_file is not None,
        reject_reason=p.reject_reason,
        created_at=p.created_at,
        confirmed_at=p.confirmed_at,
    )


@router.get("/methods", response_model=list[PaymentMethodOut])
async def payment_methods() -> list[PaymentMethodOut]:
    return [
        PaymentMethodOut(
            method=m.method,
            account_kind=m.account_kind,
            account=m.account,
            recipient=m.recipient,
            fee_percent=m.fee_percent,
            banks=[BankLinkOut(code=b.code, url=b.url) for b in m.banks],
        )
        for m in get_payment_provider().methods()
    ]


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_payment)
async def create_payment(
    request: Request,
    response: Response,
    body: PaymentCreateIn,
    user: CurrentUser,
    session: SessionDep,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> PaymentOut:
    if not IDEMPOTENCY_RE.fullmatch(idempotency_key):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="bad_idempotency_key")
    # Plain value: ORM objects expire on rollback and must not be touched after it.
    user_id = user.id

    async def existing() -> Payment | None:
        result = await session.scalars(
            select(Payment).where(
                Payment.user_id == user_id, Payment.idempotency_key == idempotency_key
            )
        )
        return result.first()

    def replay(found: Payment) -> PaymentOut:
        if found.plan_id != body.plan_id or found.method != body.method:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="idempotency_key_reused")
        response.status_code = status.HTTP_200_OK
        return to_out(found)

    if (found := await existing()) is not None:
        return replay(found)

    if body.method not in {m.method for m in get_payment_provider().methods()}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="method_unavailable")

    plan = await session.get(Plan, body.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="plan_not_found")

    open_count = await session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.user_id == user_id, Payment.status.in_(OPEN_STATUSES))
    )
    if (open_count or 0) >= MAX_OPEN_PAYMENTS:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="too_many_open_payments")

    payment = Payment(
        user_id=user_id,
        plan_id=plan.id,
        idempotency_key=idempotency_key,
        provider=get_payment_provider().name,
        method=body.method,
        # Snapshot of the plan: later price changes do not affect this payment.
        amount_dirams=plan.price_dirams,
        duration_days=plan.duration_days,
        device_limit=plan.device_limit,
    )
    session.add(payment)
    try:
        await session.commit()
    except IntegrityError:
        # Same key sent twice in parallel: the unique constraint let only one insert win.
        await session.rollback()
        if (found := await existing()) is not None:
            return replay(found)
        raise
    await session.refresh(payment)
    return to_out(payment)


@router.get("", response_model=list[PaymentOut])
async def my_payments(user: CurrentUser, session: SessionDep) -> list[PaymentOut]:
    rows = await session.scalars(
        select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    )
    return [to_out(p) for p in rows]


@router.post("/{payment_id}/receipt", response_model=PaymentOut)
@limiter.limit(settings.rate_limit_payment)
async def upload_receipt(
    request: Request,
    payment_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> PaymentOut:
    payment = await session.scalar(
        select(Payment)
        .where(Payment.id == payment_id, Payment.user_id == user.id)
        .with_for_update()
    )
    if payment is None:
        # Same answer for "not yours" and "does not exist" (no IDOR probing).
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    if payment.status not in OPEN_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="payment_closed")

    new_name = await save_receipt(file)
    old_name = payment.receipt_file
    payment.receipt_file = new_name
    payment.status = PaymentStatus.PENDING_REVIEW
    try:
        await session.commit()
    except Exception:
        delete_receipt(new_name)
        raise
    if old_name:
        delete_receipt(old_name)
    await session.refresh(payment)
    plan_code = await session.scalar(select(Plan.code).where(Plan.id == payment.plan_id))
    background.add_task(
        notify_admins_new_receipt,
        str(payment.id),
        format_tjs(payment.amount_dirams),
        plan_code or "?",
        payment.method.value,
        f"@{user.telegram_username}" if user.telegram_username else (user.email or "telegram"),
    )
    return to_out(payment)


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(payment_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> PaymentOut:
    payment = await session.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user.id)
    )
    if payment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="not_found")
    return to_out(payment)
