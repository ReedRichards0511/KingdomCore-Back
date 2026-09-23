from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import asyncpg

if TYPE_CHECKING:
    from kingdom.platform.settings import DatabaseSettings


async def _init_connection(connection: asyncpg.Connection[Any]) -> None:
    await connection.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )
    await connection.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def create_pool(settings: DatabaseSettings) -> asyncpg.Pool[Any]:
    pool = await asyncpg.create_pool(
        dsn=settings.url.get_secret_value(),
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
        command_timeout=settings.command_timeout,
        statement_cache_size=settings.statement_cache_size,
        init=_init_connection,
    )
    if pool is None:  # pragma: no cover
        raise RuntimeError("No se pudo crear el pool de conexiones")
    return pool


async def close_pool(pool: asyncpg.Pool[Any]) -> None:
    await pool.close()
