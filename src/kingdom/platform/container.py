from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from dependency_injector import containers, providers

from kingdom.contexts.identity.application.use_cases.change_password import (
    ChangePassword,
)
from kingdom.contexts.identity.application.use_cases.get_account_profile import (
    GetAccountProfile,
)
from kingdom.contexts.identity.application.use_cases.refresh_session import (
    RefreshSession,
)
from kingdom.contexts.identity.application.use_cases.resolve_current_account import (
    ResolveCurrentAccount,
)
from kingdom.contexts.identity.application.use_cases.sign_in import SignIn
from kingdom.contexts.identity.infrastructure.repositories.account_profile_query import (
    PostgresAccountProfileQuery,
)
from kingdom.contexts.identity.infrastructure.repositories.user_account_repository import (
    PostgresUserAccountRepository,
)
from kingdom.contexts.identity.infrastructure.supabase.identity_provider import (
    SupabaseIdentityProvider,
)
from kingdom.contexts.identity.infrastructure.supabase.token_verifier import (
    SupabaseTokenVerifier,
)
from kingdom.contexts.identity.infrastructure.throttling.in_memory_sign_in_throttle import (
    InMemorySignInThrottle,
)
from kingdom.platform.settings import Settings, get_settings
from kingdom.shared.infrastructure.clock import SystemClock
from kingdom.shared.infrastructure.database.connection import close_pool, create_pool
from kingdom.shared.infrastructure.database.unit_of_work import PostgresUnitOfWork
from kingdom.shared.infrastructure.id_generator import Uuid7Generator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import asyncpg

    from kingdom.contexts.identity.application.ports.sign_in_throttle import (
        SignInThrottle,
    )
    from kingdom.contexts.identity.domain.ports.identity_provider import IdentityProvider
    from kingdom.contexts.identity.domain.ports.token_verifier import TokenVerifier
    from kingdom.shared.domain.ports.clock import Clock


async def _pool_resource(settings: Settings) -> AsyncIterator[asyncpg.Pool[Any]]:
    pool = await create_pool(settings.database)
    try:
        yield pool
    finally:
        await close_pool(pool)


async def _supabase_client_resource(
    settings: Settings,
) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=settings.supabase.http_timeout_seconds) as client:
        yield client


def _build_sign_in(
    pool: asyncpg.Pool[Any],
    identity_provider: IdentityProvider,
    clock: Clock,
    throttle: SignInThrottle,
) -> SignIn:
    uow = PostgresUnitOfWork(pool)
    return SignIn(
        identity_provider=identity_provider,
        accounts=PostgresUserAccountRepository(unit_of_work=uow),
        clock=clock,
        unit_of_work=uow,
        throttle=throttle,
    )


def _build_refresh_session(
    pool: asyncpg.Pool[Any], identity_provider: IdentityProvider
) -> RefreshSession:
    uow = PostgresUnitOfWork(pool)
    return RefreshSession(
        identity_provider=identity_provider,
        accounts=PostgresUserAccountRepository(unit_of_work=uow),
        unit_of_work=uow,
    )


def _build_change_password(
    pool: asyncpg.Pool[Any],
    identity_provider: IdentityProvider,
    clock: Clock,
    throttle: SignInThrottle,
) -> ChangePassword:
    uow = PostgresUnitOfWork(pool)
    return ChangePassword(
        identity_provider=identity_provider,
        accounts=PostgresUserAccountRepository(unit_of_work=uow),
        clock=clock,
        unit_of_work=uow,
        throttle=throttle,
    )


def _build_resolve_current_account(
    pool: asyncpg.Pool[Any], token_verifier: TokenVerifier
) -> ResolveCurrentAccount:
    uow = PostgresUnitOfWork(pool)
    return ResolveCurrentAccount(
        token_verifier=token_verifier,
        accounts=PostgresUserAccountRepository(unit_of_work=uow),
        unit_of_work=uow,
    )


def _build_get_account_profile(pool: asyncpg.Pool[Any]) -> GetAccountProfile:
    uow = PostgresUnitOfWork(pool)
    return GetAccountProfile(
        profiles=PostgresAccountProfileQuery(unit_of_work=uow),
        unit_of_work=uow,
    )


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["kingdom.contexts", "kingdom.shared.api"],
    )

    settings: providers.Provider[Settings] = providers.Singleton(get_settings)

    pool: providers.Provider[Any] = providers.Resource(_pool_resource, settings=settings)

    clock: providers.Provider[SystemClock] = providers.Singleton(SystemClock)

    id_generator: providers.Provider[Uuid7Generator] = providers.Singleton(Uuid7Generator)

    unit_of_work: providers.Provider[PostgresUnitOfWork] = providers.Factory(
        PostgresUnitOfWork,
        pool=pool,
    )

    supabase_http_client: providers.Provider[httpx.AsyncClient] = providers.Resource(
        _supabase_client_resource,
        settings=settings,
    )

    identity_provider: providers.Provider[SupabaseIdentityProvider] = providers.Singleton(
        SupabaseIdentityProvider,
        settings=settings.provided.supabase,
        client=supabase_http_client,
    )

    token_verifier: providers.Provider[SupabaseTokenVerifier] = providers.Singleton(
        SupabaseTokenVerifier,
        settings=settings.provided.supabase,
    )

    sign_in_throttle: providers.Provider[InMemorySignInThrottle] = providers.Singleton(
        InMemorySignInThrottle,
        clock=clock,
        max_failures=settings.provided.auth.max_failed_sign_ins,
        window_seconds=settings.provided.auth.failed_sign_in_window_seconds,
        max_tracked_keys=settings.provided.auth.max_tracked_sign_in_keys,
    )

    sign_in: providers.Provider[SignIn] = providers.Factory(
        _build_sign_in,
        pool=pool,
        identity_provider=identity_provider,
        clock=clock,
        throttle=sign_in_throttle,
    )

    refresh_session: providers.Provider[RefreshSession] = providers.Factory(
        _build_refresh_session,
        pool=pool,
        identity_provider=identity_provider,
    )

    change_password: providers.Provider[ChangePassword] = providers.Factory(
        _build_change_password,
        pool=pool,
        identity_provider=identity_provider,
        clock=clock,
        throttle=sign_in_throttle,
    )

    resolve_current_account: providers.Provider[ResolveCurrentAccount] = providers.Factory(
        _build_resolve_current_account,
        pool=pool,
        token_verifier=token_verifier,
    )

    get_account_profile: providers.Provider[GetAccountProfile] = providers.Factory(
        _build_get_account_profile,
        pool=pool,
    )


def build_container() -> Container:
    return Container()
