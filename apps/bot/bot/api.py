"""Bot -> Payvast API over the internal network. The bot never touches the database."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp

from bot.config import BotSettings


class ApiUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Profile:
    locale: str
    is_admin: bool
    subscription_status: str | None
    expires_at: datetime | None
    days_left: int | None
    device_limit: int | None
    pending_payments: int


class PayvastApi:
    def __init__(self, settings: BotSettings) -> None:
        self._base = settings.api_url.rstrip("/")
        self._secret = settings.bot_api_secret.get_secret_value()
        self._session: aiohttp.ClientSession | None = None

    async def _http(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # trust_env=False: internal calls must never go through an outbound proxy.
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8), trust_env=False
            )
        return self._session

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()

    async def upsert(
        self,
        telegram_id: int,
        username: str | None,
        language_code: str | None,
        locale: str | None = None,
    ) -> Profile:
        if not self._secret:
            raise ApiUnavailable("BOT_API_SECRET is not set")
        body: dict[str, Any] = {
            "username": (username or None) and username[:32],
            "language_code": (language_code or None) and language_code[:8],
        }
        if locale:
            body["locale"] = locale
        http = await self._http()
        try:
            async with http.put(
                f"{self._base}/api/internal/bot/users/{telegram_id}",
                json=body,
                headers={"X-Bot-Secret": self._secret},
            ) as resp:
                if resp.status != 200:
                    raise ApiUnavailable(f"status {resp.status}")
                data = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise ApiUnavailable(type(exc).__name__) from exc
        expires = data.get("expires_at")
        return Profile(
            locale=data["locale"],
            is_admin=bool(data["is_admin"]),
            subscription_status=data.get("subscription_status"),
            expires_at=datetime.fromisoformat(expires) if expires else None,
            days_left=data.get("days_left"),
            device_limit=data.get("device_limit"),
            pending_payments=int(data.get("pending_payments") or 0),
        )
