"""In-memory panel for local development and tests. Talks to no real server."""

from dataclasses import dataclass
from datetime import datetime

from app.models import Server
from app.panel.base import PanelAdapter, PanelClient, PanelError, PanelUsage


@dataclass
class _MockClient:
    server_id: int
    device_limit: int
    expires_at: datetime
    enabled: bool = True


class MockPanelAdapter(PanelAdapter):
    def __init__(self) -> None:
        self.clients: dict[str, _MockClient] = {}

    @staticmethod
    def _link(server: Server, client_id: str) -> str:
        return f"https://{server.host}/sub/{client_id}"

    async def create_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> PanelClient:
        self.clients[client_id] = _MockClient(server.id, device_limit, expires_at)
        return PanelClient(client_id=client_id, subscription_url=self._link(server, client_id))

    async def extend_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> None:
        client = self.clients.get(client_id)
        if client is None or client.server_id != server.id:
            # Mock state is lost on restart: recreate instead of failing.
            await self.create_client(server, client_id, device_limit, expires_at)
            return
        client.expires_at = expires_at
        client.device_limit = device_limit
        client.enabled = True

    async def disable_client(self, server: Server, client_id: str) -> None:
        client = self.clients.get(client_id)
        if client is not None:
            client.enabled = False

    async def get_subscription_link(self, server: Server, client_id: str) -> str:
        return self._link(server, client_id)

    async def get_usage(self, server: Server, client_id: str) -> PanelUsage:
        if client_id not in self.clients:
            raise PanelError("unknown client")
        return PanelUsage(upload_bytes=0, download_bytes=0)
