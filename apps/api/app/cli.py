"""Management commands.

python -m app.cli seed-demo    # demo plans + mock server

There is deliberately no command that makes someone an admin. The admin is whoever signs in
through Telegram with an id listed in ADMIN_TELEGRAM_IDS (.env); nothing else grants it.
"""

import argparse
import asyncio

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Plan, Server

DEMO_PLANS = [
    # Example prices. Change them in the database for real use.
    {"code": "m1", "name_tg": "1 моҳ", "name_ru": "1 месяц", "price_dirams": 5000,
     "duration_days": 30, "device_limit": 2, "sort_order": 1},
    {"code": "m3", "name_tg": "3 моҳ", "name_ru": "3 месяца", "price_dirams": 13500,
     "duration_days": 90, "device_limit": 3, "sort_order": 2},
    {"code": "m12", "name_tg": "12 моҳ", "name_ru": "12 месяцев", "price_dirams": 48000,
     "duration_days": 365, "device_limit": 5, "sort_order": 3},
]  # fmt: skip


async def seed_demo() -> None:
    async with SessionLocal() as session:
        for data in DEMO_PLANS:
            if await session.scalar(select(Plan).where(Plan.code == data["code"])) is None:
                session.add(Plan(**data))
        if await session.scalar(select(Server).limit(1)) is None:
            session.add(Server(name="mock-1", host="mock.payvast.local", country="NL"))
        await session.commit()
    print("Demo data ready")


async def _main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seed-demo")
    args = parser.parse_args()
    try:
        if args.cmd == "seed-demo":
            await seed_demo()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
