"""Punto de entrada de la API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from kingdom import __version__
from kingdom.platform.lifespan import lifespan
from kingdom.platform.router import api_router
from kingdom.platform.settings import get_settings
from kingdom.shared.api.error_handlers import register_error_handlers


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Kingdom Core API",
        description="Gestion catequetica — Parroquia El Buen Pastor de Turubamba",
        version=__version__,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs" if not settings.app.is_production else None,
        redoc_url=None,
    )

    if settings.app.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.app.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["infra"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
