"""Payvast Telegram bot — stub only.

TODO(next stages): link Telegram account to a Payvast user, show subscription status,
notify about expiry and confirmed payments. Talk to the API, never to the DB directly.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.config import BotSettings

dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Салом! Ин боти Payvast аст. Ба зудӣ дар ин ҷо ҳолати обунаатонро мебинед.\n"
        "Привет! Это бот Payvast. Скоро здесь будет статус вашей подписки."
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = BotSettings()  # type: ignore[call-arg]
    bot = Bot(token=settings.telegram_bot_token.get_secret_value())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
