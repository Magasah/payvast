"""Telegram sign-in, the admin guard bound to ADMIN_TELEGRAM_IDS, admin term management."""

import json
import time
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AdminAuditLog, Subscription, SubscriptionStatus, User, UserRole
from app.telegram.initdata import InitDataError, sign_init_data, verify_init_data
from tests.conftest import ADMIN_TG_ID, auth_header, make_server, make_user

BOT_TOKEN = "123456:test-bot-token"


def init_data(tg_id: int, *, token: str = BOT_TOKEN, age: int = 0, **user: object) -> str:
    fields = {
        "auth_date": str(int(time.time()) - age),
        "query_id": "AAH-test",
        "user": json.dumps({"id": tg_id, "first_name": "T", **user}, separators=(",", ":")),
    }
    return sign_init_data(fields, token)


# --- initData verification ----------------------------------------------------------------


def test_verify_accepts_valid_and_rejects_tampering() -> None:
    data = init_data(42, username="ali")
    assert verify_init_data(data, BOT_TOKEN, 3600).id == 42
    with pytest.raises(InitDataError):
        verify_init_data(data, "999:other-token", 3600)
    tampered = data.replace("%22id%22%3A42", "%22id%22%3A111111")
    assert tampered != data
    with pytest.raises(InitDataError):
        verify_init_data(tampered, BOT_TOKEN, 3600)


def test_verify_rejects_old_and_missing_hash() -> None:
    with pytest.raises(InitDataError):
        verify_init_data(init_data(42, age=7200), BOT_TOKEN, 3600)
    with pytest.raises(InitDataError):
        verify_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, 3600)
    with pytest.raises(InitDataError):
        verify_init_data(init_data(42), "", 3600)


# --- login --------------------------------------------------------------------------------


async def test_telegram_login_creates_plain_user(
    client: AsyncClient, session: AsyncSession
) -> None:
    r = await client.post("/api/auth/telegram", json={"init_data": init_data(42, username="ali")})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["is_admin"] is False
    assert body["user"]["role"] == "user"
    user = await session.scalar(select(User).where(User.telegram_id == 42))
    assert user is not None and user.role == UserRole.USER and user.email is None


async def test_only_env_telegram_id_becomes_admin(client: AsyncClient) -> None:
    r = await client.post("/api/auth/telegram", json={"init_data": init_data(ADMIN_TG_ID)})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["user"]["is_admin"] is True
    ok = await client.get("/api/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200


async def test_forged_init_data_rejected(client: AsyncClient) -> None:
    forged = init_data(ADMIN_TG_ID, token="999:attacker-bot")
    r = await client.post("/api/auth/telegram", json={"init_data": forged})
    assert r.status_code == 401


async def test_role_in_db_without_env_id_gives_no_access(
    client: AsyncClient, session: AsyncSession
) -> None:
    # Someone edits the DB: role=admin with a Telegram id that is not in ADMIN_TELEGRAM_IDS.
    intruder = await make_user(session, email=None, role=UserRole.ADMIN, telegram_id=555)
    r = await client.get("/api/admin/users", headers=auth_header(intruder))
    assert r.status_code == 404
    me = await client.get("/api/auth/me", headers=auth_header(intruder))
    assert me.json()["is_admin"] is False and me.json()["role"] == "user"


async def test_db_forbids_admin_without_telegram(session: AsyncSession) -> None:
    session.add(User(email="x@example.com", password_hash="x", role=UserRole.ADMIN))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_register_cannot_set_role(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "password": "long-password-1", "role": "admin"},
    )
    assert r.status_code == 422


async def test_email_login_lockout(client: AsyncClient, session: AsyncSession) -> None:
    await make_user(session, email="lock@example.com", password="right-password-1")
    for _ in range(8):
        r = await client.post(
            "/api/auth/login", json={"email": "lock@example.com", "password": "wrong"}
        )
        assert r.status_code == 401
    # Locked now: even the right password gets the same generic answer.
    r = await client.post(
        "/api/auth/login", json={"email": "lock@example.com", "password": "right-password-1"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "invalid_credentials"


async def test_body_size_limit(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/login", content=b"x" * (7 * 1024 * 1024), headers={"Content-Type": "text/plain"}
    )
    assert r.status_code == 413


async def test_security_headers(client: AsyncClient) -> None:
    r = await client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


# --- internal bot API ---------------------------------------------------------------------


async def test_internal_bot_requires_secret(client: AsyncClient) -> None:
    r = await client.put("/api/internal/bot/users/77", json={})
    assert r.status_code == 404
    r = await client.put("/api/internal/bot/users/77", json={}, headers={"X-Bot-Secret": "nope"})
    assert r.status_code == 404
    r = await client.put(
        "/api/internal/bot/users/77",
        json={"username": "bob", "locale": "ru"},
        headers={"X-Bot-Secret": "bot-secret-bot-secret-bot-secret"},
    )
    assert r.status_code == 200
    assert r.json()["locale"] == "ru" and r.json()["is_admin"] is False


# --- admin term management ----------------------------------------------------------------


async def _admin(session: AsyncSession) -> User:
    return await make_user(session, email=None, role=UserRole.ADMIN)


async def test_grant_reduce_revoke_restore(client: AsyncClient, session: AsyncSession) -> None:
    admin = await _admin(session)
    target = await make_user(session, email="c@example.com")
    await make_server(session)
    h = auth_header(admin)
    base = f"/api/admin/users/{target.id}/subscription"

    r = await client.post(f"{base}/days", json={"days": 30, "device_limit": 2}, headers=h)
    assert r.status_code == 200, r.text
    sub = r.json()["subscription"]
    assert sub["status"] == "active" and sub["device_limit"] == 2
    assert 29 <= sub["days_left"] <= 30

    r = await client.post(f"{base}/days", json={"days": -10}, headers=h)
    assert 19 <= r.json()["subscription"]["days_left"] <= 20

    r = await client.post(f"{base}/revoke", json={"note": "spam"}, headers=h)
    assert r.json()["subscription"]["status"] == "disabled"
    user_view = await client.get("/api/subscription", headers=auth_header(target))
    assert user_view.json()["subscription_url"] is None

    r = await client.post(f"{base}/restore", headers=h)
    assert r.json()["subscription"]["status"] == "active"

    actions = [
        e["action"] for e in (await client.get("/api/admin/audit", headers=h)).json()["items"]
    ]
    assert actions[:4] == [
        "subscription.restore",
        "subscription.revoke",
        "subscription.reduce",
        "subscription.grant",
    ]


async def test_reduce_without_subscription_and_bad_days(
    client: AsyncClient, session: AsyncSession
) -> None:
    admin = await _admin(session)
    target = await make_user(session, email="d@example.com")
    h = auth_header(admin)
    base = f"/api/admin/users/{target.id}/subscription"
    assert (await client.post(f"{base}/days", json={"days": -1}, headers=h)).status_code == 409
    assert (await client.post(f"{base}/days", json={"days": 0}, headers=h)).status_code == 422
    missing = f"/api/admin/users/{uuid.uuid4()}/subscription/days"
    assert (await client.post(missing, json={"days": 5}, headers=h)).status_code == 404


async def test_parallel_grants_all_apply(client: AsyncClient, session: AsyncSession) -> None:
    import asyncio

    admin = await _admin(session)
    target = await make_user(session, email="p@example.com")
    await make_server(session)
    h = auth_header(admin)
    url = f"/api/admin/users/{target.id}/subscription/days"
    await client.post(url, json={"days": 1}, headers=h)
    results = await asyncio.gather(
        *[client.post(url, json={"days": 10}, headers=h) for _ in range(5)]
    )
    assert all(r.status_code == 200 for r in results)
    sub = await session.scalar(select(Subscription).where(Subscription.user_id == target.id))
    assert sub is not None
    await session.refresh(sub)
    days = (sub.expires_at - sub.created_at).total_seconds() / 86400
    assert 50.9 < days < 51.1  # 1 + 5 * 10, no lost update
    assert sub.status == SubscriptionStatus.ACTIVE
    count = len((await session.scalars(select(AdminAuditLog.id))).all())
    assert count == 6


async def test_search_users_and_block(client: AsyncClient, session: AsyncSession) -> None:
    admin = await _admin(session)
    await make_user(session, email="findme@example.com")
    await make_user(session, email="other@example.com")
    h = auth_header(admin)
    r = await client.get("/api/admin/users", params={"q": "findme"}, headers=h)
    assert r.json()["total"] == 1
    r = await client.get("/api/admin/users", params={"q": "%"}, headers=h)
    assert r.json()["total"] == 0  # wildcard is escaped
    uid = (await client.get("/api/admin/users", params={"q": "other"}, headers=h)).json()["items"][
        0
    ]["id"]
    r = await client.post(f"/api/admin/users/{uid}/active", json={"is_active": False}, headers=h)
    assert r.json()["user"]["is_active"] is False
    r = await client.post(
        f"/api/admin/users/{admin.id}/active", json={"is_active": False}, headers=h
    )
    assert r.status_code == 409
