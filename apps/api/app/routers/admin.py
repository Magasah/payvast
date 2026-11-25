"""Admin endpoints. Every route requires role=admin; every action is audited."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import AdminUser, SessionDep, require_admin
from app.models import Payment, PaymentStatus, Plan, Server, User
from app.panel import PanelAdapter, get_panel
from app.routers.payments import to_out
from app.routers.subscription import SubscriptionOut, subscription_out
from app.schemas.admin import (
    AdminPaymentOut,
    MoveIn,
    RejectIn,
    ServerIn,
    ServerOut,
    ServerPatch,
)
from app.schemas.payment import PaymentOut
from app.services import billing
from app.services.audit import audit
from app.services.receipts import receipt_path

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

PanelDep = Annotated[PanelAdapter, Depends(get_panel)]


def _raise(exc: billing.BillingError) -> HTTPException:
    return HTTPException(exc.http_status, detail=exc.code)


@router.get("/payments", response_model=list[AdminPaymentOut])
async def list_payments(
    session: SessionDep,
    status_filter: Annotated[PaymentStatus, Query(alias="status")] = PaymentStatus.PENDING_REVIEW,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[AdminPaymentOut]:
    rows = await session.execute(
        select(Payment, User.email, Plan.code)
        .join(User, User.id == Payment.user_id)
        .join(Plan, Plan.id == Payment.plan_id)
        .where(Payment.status == status_filter)
        .order_by(Payment.created_at)
        .limit(limit)
    )
    return [
        AdminPaymentOut(
            id=p.id,
            user_email=email,
            plan_code=code,
            method=p.method,
            amount_dirams=p.amount_dirams,
            duration_days=p.duration_days,
            status=p.status,
            has_receipt=p.receipt_file is not None,
            created_at=p.created_at,
            reviewed_at=p.reviewed_at,
            reject_reason=p.reject_reason,
        )
        for p, email, code in rows.tuples()
    ]


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
    payment_id: uuid.UUID, admin: AdminUser, session: SessionDep, panel: PanelDep
) -> PaymentOut:
    try:
        payment = await billing.confirm_payment(session, payment_id, admin, panel)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
    return to_out(payment)


@router.post("/payments/{payment_id}/reject", response_model=PaymentOut)
async def reject(
    payment_id: uuid.UUID, body: RejectIn, admin: AdminUser, session: SessionDep
) -> PaymentOut:
    try:
        payment = await billing.reject_payment(session, payment_id, admin, body.reason)
    except billing.BillingError as exc:
        raise _raise(exc) from exc
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
