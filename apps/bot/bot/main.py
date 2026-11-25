"""Payvast Telegram bot: one message with an inline menu that is edited in place.

Screens: main -> profile | settings (language) | help, plus Back / Close on every screen.
"Open app" launches the site as a Telegram Mini App; the site signs the user in from the
signed Mini App data, so the bot never handles passwords or tokens.
"""

import asyncio
import contextlib
import html
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
    User,
    WebAppInfo,
)

from bot.api import ApiUnavailable, PayvastApi, Profile
from bot.config import BotSettings
from bot.texts import t

log = logging.getLogger("payvast.bot")

settings = BotSettings()  # type: ignore[call-arg]
api = PayvastApi(settings)
dp = Dispatcher()


# --- anti-spam ------------------------------------------------------------------------------


class Throttle(BaseMiddleware):
    """Drop updates that come faster than `interval` seconds from the same user."""

    def __init__(self, interval: float) -> None:
        self.interval = interval
        self.last: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            if now - self.last.get(user.id, 0.0) < self.interval:
                if isinstance(event, CallbackQuery):
                    await event.answer(t("slow_down", _guess_lang(user)))
                return None
            self.last[user.id] = now
            if len(self.last) > 50_000:  # keep memory bounded
                self.last.clear()
        return await handler(event, data)


dp.message.middleware(Throttle(settings.throttle_seconds))
dp.callback_query.middleware(Throttle(settings.throttle_seconds))


# --- helpers --------------------------------------------------------------------------------


def _guess_lang(user: User) -> str:
    return "ru" if (user.language_code or "").startswith("ru") else "tg"


def _web_app_url(lang: str, path: str = "/cabinet") -> str | None:
    base = settings.web_app_url.rstrip("/")
    return f"{base}/{lang}{path}" if base.startswith("https://") else None


async def _profile(user: User, locale: str | None = None) -> Profile | None:
    try:
        return await api.upsert(user.id, user.username, user.language_code, locale)
    except ApiUnavailable as exc:
        log.warning("api unavailable: %s", exc)
        return None


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def main_keyboard(lang: str, is_admin: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if url := _web_app_url(lang):
        rows.append([InlineKeyboardButton(text=t("btn_open", lang), web_app=WebAppInfo(url=url))])
    rows.append(
        [_btn(t("btn_profile", lang), "m:profile"), _btn(t("btn_settings", lang), "m:settings")]
    )
    rows.append([_btn(t("btn_help", lang), "m:help")])
    if is_admin and (admin_url := _web_app_url(lang, "/admin/payments")):
        rows.append(
            [InlineKeyboardButton(text=t("btn_admin", lang), web_app=WebAppInfo(url=admin_url))]
        )
    rows.append([_btn(t("btn_close", lang), "close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard(
    lang: str, extra: list[list[InlineKeyboardButton]] | None = None
) -> InlineKeyboardMarkup:
    rows = list(extra or [])
    rows.append([_btn(t("btn_back", lang), "m:main"), _btn(t("btn_close", lang), "close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    mark = {"tg": "• " if lang == "tg" else "", "ru": "• " if lang == "ru" else ""}
    return back_keyboard(
        lang,
        [[_btn(f"{mark['tg']}Тоҷикӣ", "lang:tg"), _btn(f"{mark['ru']}Русский", "lang:ru")]],
    )


def profile_text(p: Profile, lang: str, user: User) -> str:
    name = f"@{html.escape(user.username)}" if user.username else html.escape(user.first_name)
    lines = [t("profile_title", lang), name, ""]
    until = p.expires_at.strftime("%d.%m.%Y") if p.expires_at else ""
    if p.subscription_status is None:
        lines.append(t("sub_none", lang))
    elif p.subscription_status == "active":
        lines.append(t("sub_active", lang, until=until, days=p.days_left, devices=p.device_limit))
    elif p.subscription_status == "expired":
        lines.append(t("sub_expired", lang, until=until))
    else:
        lines.append(t("sub_disabled", lang))
    if p.pending_payments:
        lines += ["", t("pending", lang, n=p.pending_payments)]
    return "\n".join(lines)


def profile_keyboard(lang: str) -> InlineKeyboardMarkup:
    extra = [[_btn(t("btn_refresh", lang), "m:profile")]]
    if url := _web_app_url(lang):
        extra.insert(
            0, [InlineKeyboardButton(text=t("btn_buy", lang), web_app=WebAppInfo(url=url))]
        )
    return back_keyboard(lang, extra)


async def _edit(cb: CallbackQuery, text: str, markup: InlineKeyboardMarkup) -> None:
    if not isinstance(cb.message, Message):
        await cb.answer()
        return
    with contextlib.suppress(TelegramBadRequest):  # "message is not modified"
        await cb.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await cb.answer()


# --- handlers -------------------------------------------------------------------------------


@dp.message(CommandStart())
@dp.message(Command("menu"))
async def start(message: Message) -> None:
    if message.from_user is None:
        return
    p = await _profile(message.from_user)
    lang = p.locale if p else _guess_lang(message.from_user)
    if p is None:
        await message.answer(t("api_down", lang))
        return
    await message.answer(
        t("welcome", lang), reply_markup=main_keyboard(lang, p.is_admin), parse_mode="HTML"
    )


@dp.message(Command("lang"))
async def lang_cmd(message: Message) -> None:
    if message.from_user is None:
        return
    p = await _profile(message.from_user)
    lang = p.locale if p else _guess_lang(message.from_user)
    await message.answer(
        t("settings_title", lang), reply_markup=settings_keyboard(lang), parse_mode="HTML"
    )


@dp.callback_query(F.data == "m:main")
async def to_main(cb: CallbackQuery) -> None:
    p = await _profile(cb.from_user)
    lang = p.locale if p else _guess_lang(cb.from_user)
    if p is None:
        await cb.answer(t("api_down", lang), show_alert=True)
        return
    await _edit(cb, t("welcome", lang), main_keyboard(lang, p.is_admin))


@dp.callback_query(F.data == "m:profile")
async def to_profile(cb: CallbackQuery) -> None:
    p = await _profile(cb.from_user)
    lang = p.locale if p else _guess_lang(cb.from_user)
    if p is None:
        await cb.answer(t("api_down", lang), show_alert=True)
        return
    await _edit(cb, profile_text(p, lang, cb.from_user), profile_keyboard(lang))


@dp.callback_query(F.data == "m:settings")
async def to_settings(cb: CallbackQuery) -> None:
    p = await _profile(cb.from_user)
    lang = p.locale if p else _guess_lang(cb.from_user)
    await _edit(cb, t("settings_title", lang), settings_keyboard(lang))


@dp.callback_query(F.data.in_({"lang:tg", "lang:ru"}))
async def set_lang(cb: CallbackQuery) -> None:
    new = "ru" if cb.data == "lang:ru" else "tg"
    p = await _profile(cb.from_user, locale=new)
    if p is None:
        await cb.answer(t("api_down", new), show_alert=True)
        return
    if isinstance(cb.message, Message):
        with contextlib.suppress(TelegramBadRequest):
            await cb.message.edit_text(
                t("settings_title", new), reply_markup=settings_keyboard(new), parse_mode="HTML"
            )
    await cb.answer(t("lang_saved", new))


@dp.callback_query(F.data == "m:help")
async def to_help(cb: CallbackQuery) -> None:
    p = await _profile(cb.from_user)
    lang = p.locale if p else _guess_lang(cb.from_user)
    await _edit(cb, t("help", lang), back_keyboard(lang))


@dp.callback_query(F.data == "close")
async def close(cb: CallbackQuery) -> None:
    if isinstance(cb.message, Message):
        try:
            await cb.message.delete()
        except TelegramBadRequest:
            # Messages older than 48h cannot be deleted: just remove the buttons.
            with contextlib.suppress(TelegramBadRequest):
                await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()


@dp.callback_query()
async def unknown_callback(cb: CallbackQuery) -> None:
    await cb.answer()


@dp.message()
async def anything_else(message: Message) -> None:
    await start(message)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # aiohttp/aiogram never log the token, but keep library noise down anyway.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await dp.start_polling(bot)
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
