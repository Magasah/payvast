from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan, Server
from app.panel import MockPanelAdapter
from app.services.servers import pick_server


async def test_list_plans_only_active_sorted(client: AsyncClient, session: AsyncSession) -> None:
    session.add_all(
        [
            Plan(code="b", name_tg="Б", name_ru="Б", price_dirams=200, duration_days=60,
                 device_limit=2, sort_order=2),
            Plan(code="a", name_tg="А", name_ru="А", price_dirams=100, duration_days=30,
                 device_limit=1, sort_order=1),
            Plan(code="off", name_tg="X", name_ru="X", price_dirams=1, duration_days=1,
                 device_limit=1, is_active=False),
        ]
    )  # fmt: skip
    await session.commit()
    r = await client.get("/api/plans")
    assert r.status_code == 200
    assert [p["code"] for p in r.json()] == ["a", "b"]


async def test_pick_server_skips_blocked(session: AsyncSession) -> None:
    session.add_all(
        [
            Server(name="blocked", host="b.example", country="NL", is_blocked=True),
            Server(name="ok", host="ok.example", country="DE"),
        ]
    )
    await session.commit()
    server = await pick_server(session)
    assert server is not None
    assert server.name == "ok"


async def test_mock_panel_lifecycle() -> None:
    panel = MockPanelAdapter()
    server = Server(id=1, name="s", host="h.example", country="NL")
    exp = datetime.now(UTC) + timedelta(days=30)
    client = await panel.create_client(server, "cid", 2, exp)
    assert client.subscription_url == "https://h.example/sub/cid"
    await panel.extend_client(server, "cid", 3, exp + timedelta(days=30))
    assert panel.clients["cid"].expires_at == exp + timedelta(days=30)
    await panel.disable_client(server, "cid")
    assert panel.clients["cid"].enabled is False
