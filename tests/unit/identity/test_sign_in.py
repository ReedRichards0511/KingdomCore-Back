from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.factories import DEFAULT_EXTERNAL_USER_ID, make_user_account
from tests.fakes.identity import (
    FakeIdentityProvider,
    FakeUnitOfWork,
    FakeUserAccountRepository,
)

from kingdom.contexts.identity.application.use_cases.sign_in import (
    SignIn,
    SignInCommand,
)
from kingdom.contexts.identity.domain.errors import (
    AccountDisabled,
    AccountNotProvisioned,
    InvalidCredentials,
    TooManySignInAttempts,
)
from kingdom.contexts.identity.domain.value_objects.auth_session import AuthSession
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.infrastructure.throttling.in_memory_sign_in_throttle import (
    InMemorySignInThrottle,
)
from kingdom.shared.infrastructure.clock import FrozenClock


async def test_el_inicio_de_sesion_registra_la_hora() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(national_id=nid, external_user_id=DEFAULT_EXTERNAL_USER_ID)
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    fixed_time = datetime(2026, 10, 4, 14, 0, tzinfo=UTC)
    clock = FrozenClock(fixed_time)

    use_case = SignIn(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    result = await use_case.execute(SignInCommand(national_id=nid, password="Temporal123"))

    assert result.session.access_token == "fake-access-token-1804470738"
    assert result.must_change_password is True
    assert account.last_login_at == fixed_time
    assert repo.logins == [account.id]
    assert uow.committed is True


async def test_credenciales_incorrectas_no_tocan_la_base() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Correcta123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(national_id=nid, external_user_id=DEFAULT_EXTERNAL_USER_ID)
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 14, 0, tzinfo=UTC))

    use_case = SignIn(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(InvalidCredentials):
        await use_case.execute(SignInCommand(national_id=nid, password="Erronea123"))

    assert not repo.logins
    assert not uow.committed


async def test_una_cuenta_sin_registro_local_cierra_la_sesion_en_supabase() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    repo = FakeUserAccountRepository([])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 14, 0, tzinfo=UTC))

    use_case = SignIn(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(AccountNotProvisioned):
        await use_case.execute(SignInCommand(national_id=nid, password="Temporal123"))

    assert ("fake-access-token-1804470738", False) in provider.signed_out_tokens


async def test_una_cuenta_desactivada_cierra_la_sesion_en_supabase() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        is_active=False,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 14, 0, tzinfo=UTC))

    use_case = SignIn(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(AccountDisabled):
        await use_case.execute(SignInCommand(national_id=nid, password="Temporal123"))

    assert ("fake-access-token-1804470738", False) in provider.signed_out_tokens


async def test_con_el_documento_bloqueado_no_se_llama_a_supabase() -> None:
    class ShouldNotBeCalledProvider(FakeIdentityProvider):
        async def sign_in(self, national_id: NationalId, password: str) -> AuthSession:
            raise AssertionError("No se debio llamar a Supabase")

    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = ShouldNotBeCalledProvider()
    account = make_user_account(national_id=nid, external_user_id=DEFAULT_EXTERNAL_USER_ID)
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 14, 0, tzinfo=UTC))
    throttle = InMemorySignInThrottle(clock=clock, max_failures=5)
    key = f"{nid.document_type.value}:{nid.number}"
    for _ in range(5):
        throttle.record_failure(key)

    use_case = SignIn(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=throttle,
    )

    with pytest.raises(TooManySignInAttempts):
        await use_case.execute(SignInCommand(national_id=nid, password="Temporal123"))

    assert not repo.logins
    assert not uow.committed
