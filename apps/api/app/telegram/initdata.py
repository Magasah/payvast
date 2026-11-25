"""Verify Telegram Mini App (WebApp) initData.

Algorithm from https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
  data_check_string = "\\n".join(sorted(f"{k}={v}" for every field except hash))
  secret_key        = HMAC_SHA256(key="WebAppData", msg=bot_token)
  hash              = hex(HMAC_SHA256(key=secret_key, msg=data_check_string))
Only the bot that owns the token can produce a valid hash, so the Telegram id inside is trusted.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode

MAX_INIT_DATA_LEN = 4096


class InitDataError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    username: str | None
    language_code: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Build a signed initData string. Used by tests and local tooling only."""
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    digest = hmac.new(_secret_key(bot_token), check.encode(), hashlib.sha256).hexdigest()
    return urlencode({**fields, "hash": digest})


def verify_init_data(
    init_data: str, bot_token: str, max_age_seconds: int, now: float | None = None
) -> TelegramUser:
    if not bot_token:
        raise InitDataError("telegram_disabled")
    if not init_data or len(init_data) > MAX_INIT_DATA_LEN:
        raise InitDataError("bad_init_data")
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InitDataError("bad_init_data") from exc
    fields: dict[str, str] = {}
    for key, value in pairs:
        if key in fields:  # duplicated keys are never produced by Telegram
            raise InitDataError("bad_init_data")
        fields[key] = value
    received = fields.pop("hash", "")
    if not received:
        raise InitDataError("bad_init_data")

    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    expected = hmac.new(_secret_key(bot_token), check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received.lower()):
        raise InitDataError("bad_signature")

    try:
        auth_date = int(fields["auth_date"])
        raw_user = json.loads(fields["user"])
        user_id = int(raw_user["id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InitDataError("bad_init_data") from exc
    current = time.time() if now is None else now
    if auth_date > current + 60 or current - auth_date > max_age_seconds:
        raise InitDataError("expired")
    if user_id <= 0:
        raise InitDataError("bad_init_data")

    username = raw_user.get("username")
    lang = raw_user.get("language_code")
    return TelegramUser(
        id=user_id,
        username=username[:32] if isinstance(username, str) else None,
        language_code=lang[:8] if isinstance(lang, str) else None,
    )
