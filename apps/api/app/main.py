"""FastAPI entrypoint."""

from fastapi import FastAPI

from app.config import get_settings


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

    @app.get("/api/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
