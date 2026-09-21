"""Raiz de composicion.

Aqui, y solo aqui, se decide que implementacion concreta satisface cada
puerto. Un caso de uso recibe sus colaboradores por constructor y nunca
construye nada por su cuenta.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dependency_injector import containers, providers

from kingdom.platform.settings import Settings, get_settings
from kingdom.shared.infrastructure.clock import SystemClock
from kingdom.shared.infrastructure.database.connection import close_pool, create_pool
from kingdom.shared.infrastructure.database.unit_of_work import PostgresUnitOfWork
from kingdom.shared.infrastructure.id_generator import Uuid7Generator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import asyncpg


async def _pool_resource(settings: Settings) -> AsyncIterator[asyncpg.Pool[Any]]:
    pool = await create_pool(settings.database)
    try:
        yield pool
    finally:
        await close_pool(pool)


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["kingdom.contexts"],
    )

    settings: providers.Provider[Settings] = providers.Singleton(get_settings)

    # --- Adaptadores transversales -----------------------------------------
    pool: providers.Provider[Any] = providers.Resource(_pool_resource, settings=settings)

    clock: providers.Provider[SystemClock] = providers.Singleton(SystemClock)

    id_generator: providers.Provider[Uuid7Generator] = providers.Singleton(Uuid7Generator)

    # Factory, no Singleton: cada caso de uso abre su propia transaccion.
    unit_of_work: providers.Provider[PostgresUnitOfWork] = providers.Factory(
        PostgresUnitOfWork,
        pool=pool,
    )

    # --- Contextos ----------------------------------------------------------
    # Conforme cada contexto reciba sus repositorios y casos de uso, se
    # declaran aqui:
    #
    #   person_repository = providers.Factory(
    #       PostgresPersonRepository, unit_of_work=unit_of_work
    #   )
    #   register_person = providers.Factory(
    #       RegisterPerson,
    #       persons=person_repository,
    #       clock=clock,
    #       ids=id_generator,
    #   )


def build_container() -> Container:
    return Container()
