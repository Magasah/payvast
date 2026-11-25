import asyncio
import io
import os
import uuid
from pathlib import Path

from httpx import AsyncClient, Response
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment
from tests.conftest import auth_header, make_plan, make_user, png_bytes


def key() -> str:
    return uuid.uuid4().hex


async def create(
    client: AsyncClient, headers: dict[str, str], plan_id: int, k: str | None = None
) -> Response:
    return await client.post(
        "/api/payments",
        json={"plan_id": plan_id, "method": "alif"},
        headers={**headers, "Idempotency-Key": k or key()},
    )


async def test_methods_show_wallets(client: AsyncClient) -> None:
    r = await client.get("/api/payments/methods")
    assert {m["method"] for m in r.json()} == {"alif", "dushanbe_city"}


async def test_create_payment_snapshots_plan(client: AsyncClient, session: AsyncSession) -> None:
    user = await make_user(session)
    plan = await make_plan(session)
    r = await create(client, auth_header(user), plan.id)
    assert r.status_code == 201
    body = r.json()
    assert body["amount_dirams"] == 5000
    assert body["status"] == "awaiting_receipt"


async def test_create_requires_auth_and_key(client: AsyncClient, session: AsyncSession) -> None:
    plan = await make_plan(session)
    r = await client.post("/api/payments", json={"plan_id": plan.id, "method": "alif"})
    assert r.status_code == 401
    user = await make_user(session)
    r = await create(client, auth_header(user), plan.id, k="short")
    assert r.status_code == 422


async def test_same_idempotency_key_returns_same_payment(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await make_user(session)
    plan = await make_plan(session)
    k = key()
    first = await create(client, auth_header(user), plan.id, k)
    second = await create(client, auth_header(user), plan.id, k)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


async def test_reused_key_with_other_plan_conflicts(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await make_user(session)
    plan = await make_plan(session)
    other = await make_plan(session, code="m3", duration_days=90, price_dirams=13500)
    k = key()
    await create(client, auth_header(user), plan.id, k)
    r = await create(client, auth_header(user), other.id, k)
    assert r.status_code == 409


async def test_parallel_requests_with_same_key_create_one_payment(
    client: AsyncClient, session: AsyncSession
) -> None:
    user = await make_user(session)
    plan = await make_plan(session)
    k = key()
    results = await asyncio.gather(
        *[create(client, auth_header(user), plan.id, k) for _ in range(8)]
    )
    assert all(r.status_code in (200, 201) for r in results)
    assert len({r.json()["id"] for r in results}) == 1
    count = await session.scalar(select(func.count()).select_from(Payment))
    assert count == 1


async def test_open_payments_are_limited(client: AsyncClient, session: AsyncSession) -> None:
    user = await make_user(session)
    plan = await make_plan(session)
    codes = [(await create(client, auth_header(user), plan.id)).status_code for _ in range(4)]
    assert codes == [201, 201, 201, 409]


async def _new_payment(client: AsyncClient, session: AsyncSession) -> tuple[dict[str, str], str]:
    user = await make_user(session)
    plan = await make_plan(session)
    headers = auth_header(user)
    r = await create(client, headers, plan.id)
    return headers, r.json()["id"]


async def test_upload_valid_receipt(client: AsyncClient, session: AsyncSession) -> None:
    headers, pid = await _new_payment(client, session)
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("my receipt.png", png_bytes(), "image/png")},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "pending_review"
    stored = await session.scalar(select(Payment.receipt_file))
    assert stored is not None
    assert stored != "my receipt.png"
    assert stored.endswith(".png") and len(stored) == 36
    path = Path(os.environ["UPLOAD_DIR"]) / stored
    assert path.exists()
    assert oct(path.stat().st_mode & 0o777) == "0o600"


async def test_receipt_exif_is_stripped(client: AsyncClient, session: AsyncSession) -> None:
    headers, pid = await _new_payment(client, session)
    img = Image.new("RGB", (30, 30))
    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMaker"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("r.jpg", buf.getvalue(), "image/jpeg")},
        headers=headers,
    )
    assert r.status_code == 200
    stored = await session.scalar(select(Payment.receipt_file))
    data = (Path(os.environ["UPLOAD_DIR"]) / str(stored)).read_bytes()
    assert b"SecretCameraMaker" not in data


async def test_upload_rejects_fake_image(client: AsyncClient, session: AsyncSession) -> None:
    headers, pid = await _new_payment(client, session)
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("x.png", b"<?php system($_GET['c']); ?>", "image/png")},
        headers=headers,
    )
    assert r.status_code == 415


async def test_upload_rejects_non_image_content_type(
    client: AsyncClient, session: AsyncSession
) -> None:
    headers, pid = await _new_payment(client, session)
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("x.pdf", png_bytes(), "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 415


async def test_upload_rejects_too_large(client: AsyncClient, session: AsyncSession) -> None:
    headers, pid = await _new_payment(client, session)
    big = png_bytes() + b"\0" * (5 * 1024 * 1024)
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("big.png", big, "image/png")},
        headers=headers,
    )
    assert r.status_code == 413


async def test_cannot_upload_to_someone_elses_payment(
    client: AsyncClient, session: AsyncSession
) -> None:
    _, pid = await _new_payment(client, session)
    intruder = await make_user(session, email="intruder@example.com")
    r = await client.post(
        f"/api/payments/{pid}/receipt",
        files={"file": ("r.png", png_bytes(), "image/png")},
        headers=auth_header(intruder),
    )
    assert r.status_code == 404
