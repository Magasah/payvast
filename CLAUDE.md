# Payvast

Web app to sell and manage subscriptions for a secure connection (VLESS + Reality on Xray)
for Tajik migrants in Russia. UI languages: Tajik (`tg`, default) and Russian (`ru`).

User flow: register → pick a plan → pay manually (Alif / Dushanbe City) and upload a receipt →
admin confirms → subscription is activated automatically → user sees the subscription link,
QR code, expiry date and setup instructions (Android, iOS, Windows).

## Monorepo

| Path        | What                                                                       |
|-------------|----------------------------------------------------------------------------|
| `apps/api`  | FastAPI, Python 3.12, SQLAlchemy 2.0 async, Alembic, Pydantic v2 (uv)      |
| `apps/web`  | Next.js 14 App Router, TypeScript, Tailwind, next-intl (`tg`/`ru`)         |
| `apps/bot`  | aiogram 3 stub only, no business logic yet                                 |
| `infra`     | `docker-compose.yml` (db, api, web), `.env.example`                        |

The stack is fixed. Do not change it without the owner's consent.

## Commands

```bash
# Everything in docker
cp infra/.env.example infra/.env   # then edit secrets
docker compose -f infra/docker-compose.yml up --build

# API (from apps/api)
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy app
uv run pytest                      # needs TEST_DATABASE_URL (PostgreSQL)
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
uv run python -m app.cli create-admin --email admin@example.com

# Web (from apps/web)
npm install
npm run lint && npm run typecheck
npm run dev                        # proxies /api/* to API_INTERNAL_URL (default http://localhost:8000)
```

## Architecture rules

- **PanelAdapter** (`apps/api/app/panel/`): interface to the VPN panel. `MockPanelAdapter` works
  without a server. `ThreeXUIAdapter` is a stub with TODOs until stage 2: never write the 3x-ui
  API from memory. Selected via `PANEL_ADAPTER` env.
- **PaymentProvider** (`apps/api/app/payments/`): MVP is `ManualPaymentProvider`.
- **Servers**: `servers` table; a user's subscription points to a server and can be moved.
- **Money**: confirming a payment and extending a subscription happen in ONE transaction with
  `SELECT ... FOR UPDATE` on the payment row, a status check, and a unique idempotency key.
  Never split this into separate transactions. Prices are integers in dirams (1 somoni = 100).
- **Admin**: every admin endpoint requires role `admin` and writes to `admin_audit_log`.

## Security rules

- Passwords: argon2. Access JWT 15 min. Refresh JWT in httpOnly + Secure + SameSite=Strict cookie,
  revoked via `users.token_version`.
- Secrets only in `.env`. `.env` is git-ignored; keep `.env.example` in sync.
- Rate limits on login, register, payment endpoints.
- Receipts: images only (JPEG/PNG/WebP, checked by content), ≤ 5 MB, re-encoded without metadata,
  random file names, served only to admins.
- No-logs: never log or store client IPs or traffic. Uvicorn runs with `--no-access-log`.
- Site copy: describe the product as "защищённое подключение" / "пайвасти ҳифзшуда".
  No wording about bypassing blocks.

## Workflow

Small steps. After each step run ruff, mypy, pytest (api) and eslint, tsc (web).
