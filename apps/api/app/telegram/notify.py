"""Best-effort Telegram notifications from the API (receipt uploaded, payment reviewed).

Runs in FastAPI background tasks after the DB commit, so a Telegram outage never blocks or
rolls back money operations. The bot token is part of the request URL: never log URLs or
exception messages from httpx here, only the exception type.
"""

import html
import logging
from typing import Any

import httpx

from app.config import get_settings

log = logging.getLogger("payvast.telegram")

TEXTS: dict[str, dict[str, str]] = {
    "confirmed": {
        "tg": "<b>Пардохт тасдиқ шуд</b>\nОбуна то {expires} фаъол аст. Пайванд — дар кабинет.",
        "ru": "<b>Оплата подтверждена</b>\nПодписка активна до {expires}. Ссылка — в кабинете.",
    },
    "rejected": {
        "tg": "<b>Пардохт рад шуд</b>\nСабаб: {reason}\nЧеки дурустро аз нав фиристед.",
        "ru": "<b>Оплата отклонена</b>\nПричина: {reason}\nОтправьте верный чек заново.",
    },
    "open": {"tg": "Кушодани кабинет", "ru": "Открыть кабинет"},
}


def _button(text: str, path: str) -> dict[str, Any] | None:
    base = get_settings().web_app_url.rstrip("/")
    if not base.startswith("https://"):
        return None  # Telegram only accepts https buttons; skip in local dev
    url = f"{base}{path}"
    return {"inline_keyboard": [[{"text": text, "web_app": {"url": url}}]]}


async def send_message(chat_id: int, text: str, markup: dict[str, Any] | None = None) -> bool:
    settings = get_settings()
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        return False
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if markup:
        payload["reply_markup"] = markup
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.telegram_api_base}/bot{token}/sendMessage", json=payload
            )
        if resp.status_code != 200:
            log.warning("telegram sendMessage failed: status=%s", resp.status_code)
            return False
    except httpx.HTTPError as exc:
        log.warning("telegram sendMessage error: %s", type(exc).__name__)
        return False
    return True


async def notify_admins_new_receipt(
    payment_id: str, amount: str, plan: str, method: str, who: str
) -> None:
    text = (
        "<b>Новый чек на проверку</b>\n"
        f"Сумма: {html.escape(amount)}\n"
        f"Тариф: {html.escape(plan)} · {html.escape(method)}\n"
        f"Клиент: {html.escape(who)}\n"
        f"<code>{html.escape(payment_id)}</code>"
    )
    markup = _button("Открыть проверку", "/ru/admin/payments")
    for admin_id in sorted(get_settings().admin_ids):
        await send_message(admin_id, text, markup)


async def notify_user_confirmed(chat_id: int, locale: str, expires: str) -> None:
    lang = locale if locale in ("tg", "ru") else "tg"
    text = TEXTS["confirmed"][lang].format(expires=html.escape(expires))
    await send_message(chat_id, text, _button(TEXTS["open"][lang], f"/{lang}/cabinet"))


async def notify_user_rejected(chat_id: int, locale: str, reason: str) -> None:
    lang = locale if locale in ("tg", "ru") else "tg"
    text = TEXTS["rejected"][lang].format(reason=html.escape(reason))
    await send_message(chat_id, text, _button(TEXTS["open"][lang], f"/{lang}/cabinet"))
