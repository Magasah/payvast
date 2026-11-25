"""Application settings. All secrets come from environment variables (.env)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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

    # Manual payments: wallet details shown to the user
    payment_wallet_alif: str = ""
    payment_wallet_dc: str = ""

    # Receipts
    upload_dir: str = "./uploads"
    receipt_max_bytes: int = 5 * 1024 * 1024

    # Rate limits (slowapi syntax)
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "3/minute"
    rate_limit_payment: str = "10/minute"
    rate_limit_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
