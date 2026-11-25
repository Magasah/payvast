from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: SecretStr
    # Bot -> API (internal network). The secret must match BOT_API_SECRET of the API.
    api_url: str = "http://localhost:8000"
    bot_api_secret: SecretStr = SecretStr("")
    # Public https site. Telegram only opens https Mini Apps; empty or http = button hidden.
    web_app_url: str = ""
    # Minimum seconds between two actions of one user (anti-spam).
    throttle_seconds: float = 0.7
