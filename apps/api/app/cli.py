"""Management commands.

python -m app.cli create-admin --email admin@example.com   # password from prompt
python -m app.cli seed-demo                                # demo plans + mock server
"""

import argparse
import asyncio
import getpass
import os
import sys

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import Plan, Server, User, UserRole
from app.security import hash_password

DEMO_PLANS = [
    # Example prices. Change them in the database for real use.
    {"code": "m1", "name_tg": "1 моҳ", "name_ru": "1 месяц", "price_dirams": 5000,
     "duration_days": 30, "device_limit": 2, "sort_order": 1},
    {"code": "m3", "name_tg": "3 моҳ", "name_ru": "3 месяца", "price_dirams": 13500,
     "duration_days": 90, "device_limit": 3, "sort_order": 2},
    {"code": "m12", "name_tg": "12 моҳ", "name_ru": "12 месяцев", "price_dirams": 48000,
     "duration_days": 365, "device_limit": 5, "sort_order": 3},
]  # fmt: skip


async def create_admin(email: str) -> None:
    password = os.environ.get("PAYVAST_ADMIN_PASSWORD") or getpass.getpass("Password: ")
    if len(password) < 12:
        sys.exit("Admin password must be at least 12 characters")
    try:
        email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        sys.exit(f"Invalid email: {exc}")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash=hash_password(password), role=UserRole.ADMIN)
            session.add(user)
        else:
            user.role = UserRole.ADMIN
            user.password_hash = hash_password(password)
            user.token_version += 1
        await session.commit()
    print(f"Admin ready: {email}")


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
    p_admin = sub.add_parser("create-admin")
    p_admin.add_argument("--email", required=True)
    sub.add_parser("seed-demo")
    args = parser.parse_args()
    try:
        if args.cmd == "create-admin":
            await create_admin(args.email)
        elif args.cmd == "seed-demo":
            await seed_demo()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
