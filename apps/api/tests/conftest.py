"""Test setup: a real PostgreSQL database (FOR UPDATE and constraints must be real).

TEST_DATABASE_URL must point to a database that can be dropped and recreated.
"""

import io
import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from PIL import Image

_env_file = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _env_file.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL to run tests")

# Must be set before the app (and its engine) is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="payvast-test-uploads-")
os.environ["PAYMENT_ALIF_ACCOUNT"] = "+992000000000"
os.environ["PAYMENT_ALIF_RECIPIENT"] = "M.M"
os.environ["PAYMENT_DC_ACCOUNT"] = "+992000000001"
os.environ["PAYMENT_DC_RECIPIENT"] = "M.M"
os.environ["PAYMENT_CARD_NUMBER"] = "5413 0000 0000 0000"
os.environ["PAYMENT_CARD_RECIPIENT"] = "M.M"
os.environ["ADMIN_TELEGRAM_IDS"] = "111111"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:test-bot-token"
os.environ["TELEGRAM_API_BASE"] = "http://telegram.invalid"
os.environ["BOT_API_SECRET"] = "bot-secret-bot-secret-bot-secret"
os.environ["WEB_APP_URL"] = ""
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app import models  # noqa: E402, F401
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Plan, Server, User, UserRole  # noqa: E402
from app.security import create_access_token, hash_password  # noqa: E402


async def _ensure_database() -> None:
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database}
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> AsyncIterator[None]:
    await _ensure_database()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as s:
        yield s


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # https base URL: the refresh cookie is Secure, httpx only sends it over https.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c


ADMIN_TG_ID = 111111


async def make_user(
    session: AsyncSession,
    email: str | None = "user@example.com",
    password: str = "correct-horse-1",
    role: UserRole = UserRole.USER,
    telegram_id: int | None = None,
) -> User:
    if role == UserRole.ADMIN and telegram_id is None:
        telegram_id = ADMIN_TG_ID
    user = User(
        email=email,
        password_hash=hash_password(password) if email else None,
        role=role,
        telegram_id=telegram_id,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}


async def make_plan(session: AsyncSession, **overrides: object) -> Plan:
    data: dict[str, object] = {
        "code": "m1",
        "name_tg": "1 моҳ",
        "name_ru": "1 месяц",
        "price_dirams": 5000,
        "duration_days": 30,
        "device_limit": 2,
    }
    data.update(overrides)
    plan = Plan(**data)
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def make_server(session: AsyncSession, name: str = "s1") -> Server:
    server = Server(name=name, host=f"{name}.example", country="NL")
    session.add(server)
    await session.commit()
    await session.refresh(server)
    return server


def png_bytes(size: tuple[int, int] = (20, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (10, 120, 80)).save(buf, format="PNG")
    return buf.getvalue()
