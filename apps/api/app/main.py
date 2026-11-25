"""FastAPI entrypoint."""

import logging

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware import SecurityMiddleware
from app.ratelimit import limiter
from app.routers import admin, auth, internal_bot, payments, plans, subscription

# httpx logs full request URLs at INFO; Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Payvast API",
        version="0.1.0",
        # Hide interactive docs in production.
        docs_url=None if settings.env == "prod" else "/api/docs",
        openapi_url=None if settings.env == "prod" else "/api/openapi.json",
        redoc_url=None,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SecurityMiddleware, max_body_bytes=settings.max_body_bytes)

    app.include_router(auth.router)
    app.include_router(plans.router)
    app.include_router(payments.router)
    app.include_router(subscription.router)
    app.include_router(admin.router)
    app.include_router(internal_bot.router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
