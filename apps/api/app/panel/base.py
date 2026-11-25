"""PanelAdapter: the only way the app talks to the VPN panel (Xray via 3x-ui, mock, ...).

All methods take absolute values (e.g. expires_at), never deltas, so a retried call after a
failed DB commit cannot extend a client twice.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models import Server


class PanelError(Exception):
    """The panel rejected the request or is unreachable."""


@dataclass(frozen=True, slots=True)
class PanelClient:
    client_id: str
    subscription_url: str


@dataclass(frozen=True, slots=True)
class PanelUsage:
    """Aggregate byte counters only. No per-connection or per-destination data."""

    upload_bytes: int
    download_bytes: int


class PanelAdapter(ABC):
    @abstractmethod
    async def create_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> PanelClient: ...

    @abstractmethod
    async def extend_client(
        self, server: Server, client_id: str, device_limit: int, expires_at: datetime
    ) -> None: ...

    @abstractmethod
    async def disable_client(self, server: Server, client_id: str) -> None: ...

    @abstractmethod
    async def get_subscription_link(self, server: Server, client_id: str) -> str: ...

    @abstractmethod
    async def get_usage(self, server: Server, client_id: str) -> PanelUsage: ...
