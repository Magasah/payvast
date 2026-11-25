from functools import lru_cache

from app.config import get_settings
from app.panel.base import PanelAdapter, PanelClient, PanelError, PanelUsage
from app.panel.mock import MockPanelAdapter
from app.panel.threexui import ThreeXUIAdapter


@lru_cache
def get_panel() -> PanelAdapter:
    """Adapter chosen by PANEL_ADAPTER env. Overridable in tests via dependency_overrides."""
    match get_settings().panel_adapter:
        case "mock":
            return MockPanelAdapter()
        case "3xui":
            return ThreeXUIAdapter()


__all__ = [
    "MockPanelAdapter",
    "PanelAdapter",
    "PanelClient",
    "PanelError",
    "PanelUsage",
    "ThreeXUIAdapter",
    "get_panel",
]
