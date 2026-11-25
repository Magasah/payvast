"""FastAPI entrypoint."""

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.ratelimit import limiter
from app.routers import auth


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

    app.include_router(auth.router)

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
