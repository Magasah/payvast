"""Payment confirmation and subscription extension, including concurrency."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, Payment, PaymentStatus, Subscription, User, UserRole
from app.panel import MockPanelAdapter, get_panel
from tests.conftest import app, auth_header, make_plan, make_server, make_user, png_bytes


@pytest.fixture(autouse=True)
def panel() -> MockPanelAdapter:
    mock = MockPanelAdapter()
    app.dependency_overrides[get_panel] = lambda: mock
    yield mock  # type: ignore[misc]
    app.dependency_overrides.pop(get_panel, None)


async def _pending_payment(client: AsyncClient, user: User, plan_id: int) -> str:
    headers = auth_header(user)
    r = await client.post(
        "/api/payments",
        json={"plan_id": plan_id, "method": "alif"},
        headers={**headers, "Idempotency-Key": uuid.uuid4().hex},
    )
    pid = r.json()["id"]
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("r.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert r.status_code == 200
    return str(pid)


@pytest.fixture
async def setup(client: AsyncClient, session: AsyncSession) -> tuple[User, User, int]:
    await make_server(session)
    user = await make_user(session)
    admin = await make_user(session, email="admin@example.com", role=UserRole.ADMIN)
    plan = await make_plan(session)
    return user, admin, plan.id


async def test_confirm_creates_subscription_and_audit(
    client: AsyncClient,
    session: AsyncSession,
    setup: tuple[User, User, int],
    panel: MockPanelAdapter,
) -> None:
    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)

    r = await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"

    sub = await client.get("/api/subscription", headers=auth_header(user))
    assert sub.status_code == 200
    body = sub.json()
    assert body["status"] == "active"
    assert body["days_left"] in (29, 30)
    assert body["subscription_url"].startswith("https://s1.example/sub/")
    assert len(panel.clients) == 1

    qr = await client.get("/api/subscription/qr", headers=auth_header(user))
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/svg+xml"
    assert b"<svg" in qr.content

    logs = (await session.scalars(select(AdminAuditLog))).all()
    assert [entry.action for entry in logs] == ["payment.confirm"]
    assert logs[0].admin_id == admin.id


async def test_second_payment_extends_from_current_expiry(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    user, admin, plan_id = setup
    for _ in range(2):
        pid = await _pending_payment(client, user, plan_id)
        r = await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
        assert r.status_code == 200
    sub = await session.scalar(select(Subscription))
    assert sub is not None
    expected = datetime.now(UTC) + timedelta(days=60)
    assert abs((sub.expires_at - expected).total_seconds()) < 60


async def test_expired_subscription_extends_from_now(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)
    await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    sub = await session.scalar(select(Subscription))
    assert sub is not None
    sub.expires_at = datetime.now(UTC) - timedelta(days=100)
    await session.commit()

    pid = await _pending_payment(client, user, plan_id)
    await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    session.expire_all()
    sub = await session.scalar(select(Subscription))
    assert sub is not None
    expected = datetime.now(UTC) + timedelta(days=30)
    assert abs((sub.expires_at - expected).total_seconds()) < 60


async def test_parallel_double_confirm_counts_payment_once(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    """10 admins click "confirm" on the same payment at the same moment."""
    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)
    headers = auth_header(admin)

    results = await asyncio.gather(
        *[client.post(f"/api/admin/payments/{pid}/confirm", headers=headers) for _ in range(10)]
    )

    codes = sorted(r.status_code for r in results)
    assert codes == [200] + [409] * 9
    assert all(r.json()["detail"] == "already_confirmed" for r in results if r.status_code == 409)

    sub = await session.scalar(select(Subscription))
    assert sub is not None
    expected = datetime.now(UTC) + timedelta(days=30)  # 30, not 300
    assert abs((sub.expires_at - expected).total_seconds()) < 60

    confirms = await session.scalar(
        select(func.count())
        .select_from(AdminAuditLog)
        .where(AdminAuditLog.action == "payment.confirm")
    )
    assert confirms == 1


async def test_parallel_confirm_of_two_payments_of_one_user_adds_both(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    """Two different payments confirmed at once: both count, one subscription row."""
    user, admin, plan_id = setup
    p1 = await _pending_payment(client, user, plan_id)
    p2 = await _pending_payment(client, user, plan_id)
    headers = auth_header(admin)

    results = await asyncio.gather(
        client.post(f"/api/admin/payments/{p1}/confirm", headers=headers),
        client.post(f"/api/admin/payments/{p2}/confirm", headers=headers),
    )
    assert [r.status_code for r in results] == [200, 200]

    subs = (await session.scalars(select(Subscription))).all()
    assert len(subs) == 1
    expected = datetime.now(UTC) + timedelta(days=60)
    assert abs((subs[0].expires_at - expected).total_seconds()) < 60


async def test_confirm_rejected_or_without_receipt_fails(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    user, admin, plan_id = setup
    r = await client.post(
        "/api/payments",
        json={"plan_id": plan_id, "method": "alif"},
        headers={**auth_header(user), "Idempotency-Key": uuid.uuid4().hex},
    )
    no_receipt = r.json()["id"]
    r = await client.post(f"/api/admin/payments/{no_receipt}/confirm", headers=auth_header(admin))
    assert r.status_code == 409

    pid = await _pending_payment(client, user, plan_id)
    r = await client.post(
        f"/api/admin/payments/{pid}/reject",
        json={"reason": "сумма не совпадает"},
        headers=auth_header(admin),
    )
    assert r.status_code == 200
    r = await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    assert r.status_code == 409
    assert await session.scalar(select(func.count()).select_from(Subscription)) == 0


async def test_panel_failure_rolls_back_everything(
    client: AsyncClient,
    session: AsyncSession,
    setup: tuple[User, User, int],
    panel: MockPanelAdapter,
) -> None:
    from app.panel import PanelError

    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)

    async def boom(*args: object, **kwargs: object) -> None:
        raise PanelError("down")

    panel.create_client = boom  # type: ignore[method-assign,assignment]
    r = await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    assert r.status_code == 502

    payment = await session.get(Payment, uuid.UUID(pid))
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING_REVIEW
    assert await session.scalar(select(func.count()).select_from(Subscription)) == 0
    assert await session.scalar(select(func.count()).select_from(AdminAuditLog)) == 0


async def test_admin_endpoints_require_admin(
    client: AsyncClient, setup: tuple[User, User, int]
) -> None:
    user, _, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)
    assert (await client.get("/api/admin/payments")).status_code == 401
    for method, url in [
        ("GET", "/api/admin/payments"),
        ("GET", f"/api/admin/payments/{pid}/receipt"),
        ("POST", f"/api/admin/payments/{pid}/confirm"),
        ("GET", "/api/admin/servers"),
    ]:
        r = await client.request(method, url, headers=auth_header(user))
        assert r.status_code == 403, url


async def test_admin_lists_pending_and_views_receipt(
    client: AsyncClient, session: AsyncSession, setup: tuple[User, User, int]
) -> None:
    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)
    r = await client.get("/api/admin/payments", headers=auth_header(admin))
    assert [p["id"] for p in r.json()] == [pid]
    assert r.json()[0]["user_email"] == "user@example.com"

    r = await client.get(f"/api/admin/payments/{pid}/receipt", headers=auth_header(admin))
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.headers["x-content-type-options"] == "nosniff"
    actions = (await session.scalars(select(AdminAuditLog.action))).all()
    assert actions == ["payment.view_receipt"]


async def test_move_subscription_to_other_server(
    client: AsyncClient,
    session: AsyncSession,
    setup: tuple[User, User, int],
    panel: MockPanelAdapter,
) -> None:
    user, admin, plan_id = setup
    pid = await _pending_payment(client, user, plan_id)
    await client.post(f"/api/admin/payments/{pid}/confirm", headers=auth_header(admin))
    new_server = await make_server(session, name="s2")

    sub = await session.scalar(select(Subscription))
    assert sub is not None
    r = await client.post(
        f"/api/admin/subscriptions/{sub.id}/move", json={}, headers=auth_header(admin)
    )
    assert r.status_code == 200
    assert r.json()["subscription_url"].startswith("https://s2.example/")
    assert panel.clients[sub.panel_client_id].server_id == new_server.id
