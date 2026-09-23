from __future__ import annotations

import pytest
from tests.factories import DEFAULT_EXTERNAL_USER_ID, make_user_account
from tests.fakes.identity import (
    FakeIdentityProvider,
    FakeUnitOfWork,
    FakeUserAccountRepository,
)

from kingdom.contexts.identity.application.use_cases.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from kingdom.contexts.identity.domain.errors import (
    AccountDisabled,
    AccountNotProvisioned,
    InvalidToken,
)


async def test_refrescar_sesion_devuelve_nueva_sesion() -> None:
    provider = FakeIdentityProvider(
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(external_user_id=DEFAULT_EXTERNAL_USER_ID)
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()

    use_case = RefreshSession(
        identity_provider=provider,
        accounts=repo,
        unit_of_work=uow,
    )

    result = await use_case.execute(
        RefreshSessionCommand(refresh_token="fake-refresh-token-1804470738")
    )

    assert result.session.access_token == "fake-access-token-1804470738-refreshed"
    assert result.must_change_password is True


async def test_refrescar_sesion_de_cuenta_desactivada_falla() -> None:
    provider = FakeIdentityProvider(
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        is_active=False,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()

    use_case = RefreshSession(
        identity_provider=provider,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(AccountDisabled):
        await use_case.execute(RefreshSessionCommand(refresh_token="fake-refresh-token-1804470738"))


async def test_refrescar_sesion_de_cuenta_no_provisionada_falla() -> None:
    provider = FakeIdentityProvider(
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    repo = FakeUserAccountRepository([])
    uow = FakeUnitOfWork()

    use_case = RefreshSession(
        identity_provider=provider,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(AccountNotProvisioned):
        await use_case.execute(RefreshSessionCommand(refresh_token="fake-refresh-token-1804470738"))


async def test_refrescar_sesion_con_token_invalido_falla() -> None:
    provider = FakeIdentityProvider()
    repo = FakeUserAccountRepository([])
    uow = FakeUnitOfWork()

    use_case = RefreshSession(
        identity_provider=provider,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(InvalidToken):
        await use_case.execute(RefreshSessionCommand(refresh_token="invalid-token"))
