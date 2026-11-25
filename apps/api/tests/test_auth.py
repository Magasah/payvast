from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ratelimit import limiter
from tests.conftest import auth_header, make_user

PASSWORD = "correct-horse-1"


async def test_register_sets_secure_refresh_cookie(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register", json={"email": " New@Example.com ", "password": PASSWORD}
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["role"] == "user"
    assert body["access_token"]
    cookie = r.headers["set-cookie"].lower()
    assert "pv_refresh=" in cookie
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert "password" not in r.text


async def test_register_duplicate_email(client: AsyncClient, session: AsyncSession) -> None:
    await make_user(session, email="dup@example.com")
    r = await client.post(
        "/api/auth/register", json={"email": "dup@example.com", "password": PASSWORD}
    )
    assert r.status_code == 409


async def test_register_rejects_short_password_and_extra_fields(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "short"}
    )
    assert r.status_code == 422
    r = await client.post(
        "/api/auth/register",
        json={"email": "a@example.com", "password": PASSWORD, "role": "admin"},
    )
    assert r.status_code == 422


async def test_password_is_hashed_with_argon2(client: AsyncClient, session: AsyncSession) -> None:
    user = await make_user(session)
    assert user.password_hash.startswith("$argon2id$")


async def test_login_success_and_me(client: AsyncClient, session: AsyncSession) -> None:
    await make_user(session)
    r = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": PASSWORD}
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


async def test_login_wrong_password_and_unknown_email_look_the_same(
    client: AsyncClient, session: AsyncSession
) -> None:
    await make_user(session)
    wrong = await client.post(
        "/api/auth/login", json={"email": "user@example.com", "password": "x"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "no@example.com", "password": "x"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


async def test_refresh_rotates_and_logout_revokes(
    client: AsyncClient, session: AsyncSession
) -> None:
    await make_user(session)
    await client.post("/api/auth/login", json={"email": "user@example.com", "password": PASSWORD})
    old_cookie = client.cookies.get("pv_refresh")

    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert r.json()["access_token"]

    r = await client.post("/api/auth/logout")
    assert r.status_code == 204

    # Old refresh token no longer works after logout (token_version bumped).
    client.cookies.set("pv_refresh", old_cookie or "", domain="test", path="/api/auth")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_access_token_cannot_be_used_as_refresh(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await make_user(session)
    access = auth_header(user)["Authorization"].split()[1]
    client.cookies.set("pv_refresh", access, domain="test", path="/api/auth")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 401


async def test_me_requires_token(client: AsyncClient) -> None:
    assert (await client.get("/api/auth/me")).status_code == 401
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


async def test_login_rate_limited(client: AsyncClient, session: AsyncSession) -> None:
    await make_user(session)
    limiter.enabled = True
    limiter.reset()
    try:
        codes = [
            (
                await client.post(
                    "/api/auth/login", json={"email": "user@example.com", "password": "bad"}
                )
            ).status_code
            for _ in range(7)
        ]
    finally:
        limiter.enabled = False
        limiter.reset()
    assert codes[:5] == [401] * 5
    assert codes[5] == 429
