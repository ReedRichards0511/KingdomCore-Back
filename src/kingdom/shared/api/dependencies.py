from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from kingdom.contexts.identity.application.use_cases.resolve_current_account import (
    ResolveCurrentAccount,
    ResolveCurrentAccountQuery,
)
from kingdom.contexts.identity.domain.entities.user_account import UserAccount
from kingdom.contexts.identity.domain.errors import MissingToken
from kingdom.contexts.identity.domain.value_objects.role_assignment import RoleName
from kingdom.platform.container import Container

bearer_scheme = HTTPBearer(auto_error=False)


def get_raw_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or not credentials.credentials:
        raise MissingToken()
    return credentials.credentials


@inject
async def current_account(
    token: str = Depends(get_raw_token),
    resolver: ResolveCurrentAccount = Depends(Provide[Container.resolve_current_account]),
) -> UserAccount:
    return await resolver.execute(ResolveCurrentAccountQuery(access_token=token))


def require_role(
    role: RoleName,
    *more_roles: RoleName,
) -> Callable[..., Coroutine[Any, Any, UserAccount]]:
    required = frozenset((role, *more_roles))

    async def _dependency(
        account: UserAccount = Depends(current_account),
    ) -> UserAccount:
        account.ensure_password_is_current()
        account.ensure_has_any_role(required)
        return account

    return _dependency
