from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from kingdom.platform.container import build_container
from kingdom.shared.infrastructure.logging import configure_logging, get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = build_container()
    settings = container.settings()

    configure_logging(
        level=settings.observability.log_level,
        json_output=settings.observability.log_json,
    )

    await container.init_resources()  # type: ignore[misc]
    app.state.container = container

    logger.info("application_started", env=settings.app.env.value)
    try:
        yield
    finally:
        await container.shutdown_resources()  # type: ignore[misc]
        logger.info("application_stopped")
