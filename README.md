# Payvast

Подписка на защищённое подключение (VLESS + Reality, Xray) с оплатой через Алиф, Душанбе Сити и банковскую карту.
Интерфейс на таджикском (по умолчанию) и русском.

## Быстрый старт (Docker)

Нужны Docker и Docker Compose v2.

```bash
cp infra/.env.example infra/.env
# Откройте infra/.env и замените все CHANGE_ME.
# JWT_SECRET: python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose -f infra/docker-compose.yml up -d --build

# Демо-тарифы и тестовый сервер (MockPanelAdapter)
docker compose -f infra/docker-compose.yml exec api python -m app.cli seed-demo

```

**Админ.** Админом может быть только тот, чей Telegram ID указан в `ADMIN_TELEGRAM_IDS`
в `infra/.env`. Команды «сделать админом» нет. Откройте бота, нажмите «Открыть приложение»,
и вход произойдёт через Telegram. Для всех остальных адреса `/admin` и `/api/admin/*`
отвечают 404.

Откройте http://localhost:3000. Миграции применяются автоматически при старте API.

## Локальная разработка без Docker

Нужны Python 3.12, [uv](https://docs.astral.sh/uv/), Node.js 20, PostgreSQL 16.

```bash
# База (можно взять только её из compose)
docker compose -f infra/docker-compose.yml up -d db

# API
cd apps/api
cat > .env <<'ENV'
DATABASE_URL=postgresql+asyncpg://payvast:<пароль>@localhost:5432/payvast
TEST_DATABASE_URL=postgresql+asyncpg://payvast:<пароль>@localhost:5432/payvast_test
JWT_SECRET=<случайная строка от 32 символов>
PAYMENT_ALIF_ACCOUNT=+992...
PAYMENT_ALIF_RECIPIENT=...
ADMIN_TELEGRAM_IDS=<ваш Telegram ID>
TELEGRAM_BOT_TOKEN=<токен бота>
UPLOAD_DIR=./uploads
ENV
uv sync
uv run alembic upgrade head
uv run python -m app.cli seed-demo
uv run uvicorn app.main:app --reload --no-access-log      # http://localhost:8000/api/docs

# Web (в другом терминале)
cd apps/web
npm install
npm run dev                                               # http://localhost:3000
```

## Проверки

```bash
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
cd apps/web && npm run lint && npm run typecheck && npm run build
```

Тесты API идут на настоящем PostgreSQL (`TEST_DATABASE_URL`, база создаётся сама).
Главный тест денег: `tests/test_billing.py::test_parallel_double_confirm_counts_payment_once`,
10 параллельных подтверждений одного платежа продлевают подписку ровно один раз.

## Как это работает

1. Пользователь регистрируется и выбирает тариф.
2. Создаётся платёж с `Idempotency-Key`: повторный клик не создаст второй платёж.
3. Пользователь переводит деньги на кошелёк и загружает чек (JPG/PNG/WebP до 5 МБ).
4. Админ на `/ru/admin/payments` смотрит чек и подтверждает. В одной транзакции
   платёж блокируется (`SELECT ... FOR UPDATE`), подписка создаётся или продлевается,
   клиент создаётся в VPN-панели, пишется запись в `admin_audit_log`.
5. В кабинете появляются ссылка подписки, QR-код и срок действия.

VPN-панель выбирается переменной `PANEL_ADAPTER`. Сейчас работает только `mock`;
адаптер 3x-ui (`apps/api/app/panel/threexui.py`) будет на этапе 2.

## Структура

```
apps/api   FastAPI + SQLAlchemy + Alembic
apps/web   Next.js 14 + next-intl + Tailwind
apps/bot   aiogram 3 (заготовка)
infra      docker-compose.yml, .env.example
```

Подробности для разработчиков и правила безопасности: [CLAUDE.md](CLAUDE.md).
