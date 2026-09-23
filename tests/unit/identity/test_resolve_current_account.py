from __future__ import annotations

import pytest
from tests.factories import DEFAULT_EXTERNAL_USER_ID, make_user_account
from tests.fakes.identity import (
    FakeTokenVerifier,
    FakeUnitOfWork,
    FakeUserAccountRepository,
)

from kingdom.contexts.identity.application.use_cases.resolve_current_account import (
    ResolveCurrentAccount,
    ResolveCurrentAccountQuery,
)
from kingdom.contexts.identity.domain.errors import (
    AccountDisabled,
    AccountNotProvisioned,
    InvalidToken,
)
from kingdom.contexts.identity.domain.value_objects.token_claims import TokenClaims


async def test_resolver_cuenta_valida() -> None:
    account = make_user_account(external_user_id=DEFAULT_EXTERNAL_USER_ID)
    verifier = FakeTokenVerifier(
        claims_by_token={"valid-token": TokenClaims(DEFAULT_EXTERNAL_USER_ID)}
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()

    use_case = ResolveCurrentAccount(
        token_verifier=verifier,
        accounts=repo,
        unit_of_work=uow,
    )

    resolved = await use_case.execute(ResolveCurrentAccountQuery(access_token="valid-token"))

    assert resolved.id == account.id
    assert resolved.external_user_id == DEFAULT_EXTERNAL_USER_ID


async def test_resolver_cuenta_inexistente_lanza_error() -> None:
    verifier = FakeTokenVerifier(
        claims_by_token={"unknown-token": TokenClaims(DEFAULT_EXTERNAL_USER_ID)}
    )
    repo = FakeUserAccountRepository([])
    uow = FakeUnitOfWork()

    use_case = ResolveCurrentAccount(
        token_verifier=verifier,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(AccountNotProvisioned):
        await use_case.execute(ResolveCurrentAccountQuery(access_token="unknown-token"))


async def test_resolver_cuenta_desactivada_lanza_error() -> None:
    account = make_user_account(
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        is_active=False,
    )
    verifier = FakeTokenVerifier(
        claims_by_token={"disabled-token": TokenClaims(DEFAULT_EXTERNAL_USER_ID)}
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()

    use_case = ResolveCurrentAccount(
        token_verifier=verifier,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(AccountDisabled):
        await use_case.execute(ResolveCurrentAccountQuery(access_token="disabled-token"))


async def test_resolver_token_invalido_lanza_error() -> None:
    verifier = FakeTokenVerifier()
    repo = FakeUserAccountRepository([])
    uow = FakeUnitOfWork()

    use_case = ResolveCurrentAccount(
        token_verifier=verifier,
        accounts=repo,
        unit_of_work=uow,
    )

    with pytest.raises(InvalidToken):
        await use_case.execute(ResolveCurrentAccountQuery(access_token="non-existent"))
