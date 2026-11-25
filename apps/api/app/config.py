"""Application settings. All secrets come from environment variables (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"

    database_url: str = Field(
        default="postgresql+asyncpg://payvast:payvast@localhost:5432/payvast",
    )

    # JWT
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_ttl_minutes: int = Field(default=15, ge=1, le=60)
    jwt_refresh_ttl_days: int = Field(default=30, ge=1, le=90)

    # Cookies
    cookie_secure: bool = True
    refresh_cookie_name: str = "pv_refresh"
    refresh_cookie_path: str = "/api/auth"

    # VPN panel
    panel_adapter: Literal["mock", "3xui"] = "mock"
    threexui_base_url: str = ""
    threexui_username: str = ""
    threexui_password: SecretStr = SecretStr("")

    # Admin access. Only these Telegram user ids can ever be admins; nothing else grants it.
    # Comma-separated, e.g. ADMIN_TELEGRAM_IDS=123456789
    admin_telegram_ids: str = ""

    # Telegram: bot token verifies WebApp initData and sends notifications.
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_auth_max_age_seconds: int = Field(default=86400, ge=60, le=7 * 86400)
    telegram_api_base: str = "https://api.telegram.org"
    # Shared secret for the bot -> API internal endpoints (empty = endpoints disabled).
    bot_api_secret: SecretStr = SecretStr("")
    # Public site URL, used in notification buttons.
    web_app_url: str = ""

    # Manual payments: requisites shown to the user
    payment_alif_account: str = ""
    payment_alif_recipient: str = ""
    payment_dc_account: str = ""
    payment_dc_recipient: str = ""
    payment_dc_fee_percent: int = Field(default=1, ge=0, le=10)
    payment_card_number: str = ""
    payment_card_recipient: str = ""

    # Brute force: lock an account for a while after N wrong passwords in a row.
    login_max_failures: int = Field(default=8, ge=3, le=50)
    login_lock_minutes: int = Field(default=15, ge=1, le=24 * 60)
    # Hard cap for any request body (receipts are the largest).
    max_body_bytes: int = 6 * 1024 * 1024

    # Receipts
    upload_dir: str = "./uploads"
    receipt_max_bytes: int = 5 * 1024 * 1024

    # Rate limits (slowapi syntax)
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_payment: str = "10/minute"
    # Every full page load restores the session via /refresh, so this one is looser.
    rate_limit_refresh: str = "30/minute"
    rate_limit_telegram: str = "10/minute"
    rate_limit_enabled: bool = True

    @field_validator("admin_telegram_ids")
    @classmethod
    def _check_admin_ids(cls, value: str) -> str:
        for part in value.split(","):
            if part.strip() and not part.strip().isdigit():
                raise ValueError("ADMIN_TELEGRAM_IDS must be comma-separated numeric ids")
        return value

    @property
    def admin_ids(self) -> frozenset[int]:
        return frozenset(int(p) for p in self.admin_telegram_ids.split(",") if p.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
