"""Adapter for the 3x-ui panel API. Implemented in stage 2.

TODO(stage 2): implement against the real 3x-ui API documentation for the installed panel
version. Do not guess endpoints or payloads. Needed:
  - auth/session handling (THREEXUI_BASE_URL, THREEXUI_USERNAME, THREEXUI_PASSWORD)
  - add a VLESS+Reality client to inbound `server.panel_inbound_id`
    with limitIp = device_limit and expiry = expires_at
  - update client expiry / limit, disable client
  - build the subscription URL
  - read aggregate traffic counters (no per-connection data)
"""

from datetime import datetime

from app.models import Server
from app.panel.base import PanelAdapter, PanelClient, PanelUsage

_TODO = "ThreeXUIAdapter is implemented in stage 2. Use PANEL_ADAPTER=mock."


class ThreeXUIAdapter(PanelAdapter):
    async def create_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> PanelClient:
        raise NotImplementedError(_TODO)

    async def extend_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> None:
        raise NotImplementedError(_TODO)

    async def disable_client(self, server: Server, client_id: str) -> None:
        raise NotImplementedError(_TODO)

    async def get_subscription_link(self, server: Server, client_id: str) -> str:
        raise NotImplementedError(_TODO)

    async def get_usage(self, server: Server, client_id: str) -> PanelUsage:
        raise NotImplementedError(_TODO)
