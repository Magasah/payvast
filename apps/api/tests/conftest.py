"""Test setup: a real PostgreSQL database (FOR UPDATE and constraints must be real).

TEST_DATABASE_URL must point to a database that can be dropped and recreated.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from dotenv import dotenv_values

_env_file = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _env_file.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("Set TEST_DATABASE_URL to run tests")

# Must be set before the app (and its engine) is imported.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app import models  # noqa: E402, F401
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User, UserRole  # noqa: E402
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


async def make_user(
    session: AsyncSession,
    email: str = "user@example.com",
    password: str = "correct-horse-1",
    role: UserRole = UserRole.USER,
) -> User:
    user = User(email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.value)}"}
