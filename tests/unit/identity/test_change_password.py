from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.factories import DEFAULT_EXTERNAL_USER_ID, make_user_account
from tests.fakes.identity import (
    FakeIdentityProvider,
    FakeUnitOfWork,
    FakeUserAccountRepository,
)

from kingdom.contexts.identity.application.use_cases.change_password import (
    ChangePassword,
    ChangePasswordCommand,
)
from kingdom.contexts.identity.domain.errors import (
    InvalidCurrentPassword,
    PasswordReused,
    WeakPassword,
)
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.domain.value_objects.password import NewPassword
from kingdom.contexts.identity.infrastructure.throttling.in_memory_sign_in_throttle import (
    InMemorySignInThrottle,
)
from kingdom.shared.infrastructure.clock import FrozenClock


async def test_el_cambio_apaga_la_bandera_y_devuelve_sesion_nueva() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    fixed_time = datetime(2026, 10, 4, 15, 0, tzinfo=UTC)
    clock = FrozenClock(fixed_time)

    use_case = ChangePassword(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    new_session = await use_case.execute(
        ChangePasswordCommand(
            account_external_id=DEFAULT_EXTERNAL_USER_ID,
            current_password="Temporal123",
            new_password=NewPassword("NuevaPasswordSegura2026"),
        )
    )

    assert account.must_change_password is False
    assert account.updated_at == fixed_time
    assert new_session.access_token == "fake-access-token-1804470738"
    assert repo.password_changes == [account.id]
    assert provider.credentials["1804470738"] == "NuevaPasswordSegura2026"


async def test_la_contrasena_actual_incorrecta_no_cambia_nada() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Correcta123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 15, 0, tzinfo=UTC))

    use_case = ChangePassword(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(InvalidCurrentPassword):
        await use_case.execute(
            ChangePasswordCommand(
                account_external_id=DEFAULT_EXTERNAL_USER_ID,
                current_password="Incorrecta123",
                new_password=NewPassword("NuevaPasswordSegura2026"),
            )
        )

    assert account.must_change_password is True
    assert not provider.changed_passwords
    assert not repo.password_changes


async def test_no_se_permite_repetir_la_contrasena_actual() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 15, 0, tzinfo=UTC))

    use_case = ChangePassword(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(PasswordReused):
        await use_case.execute(
            ChangePasswordCommand(
                account_external_id=DEFAULT_EXTERNAL_USER_ID,
                current_password="Temporal123",
                new_password=NewPassword("Temporal123"),
            )
        )

    assert account.must_change_password is True
    assert not provider.changed_passwords
    assert not repo.password_changes


async def test_el_cambio_cierra_todas_las_sesiones_anteriores() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 15, 0, tzinfo=UTC))

    use_case = ChangePassword(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    await use_case.execute(
        ChangePasswordCommand(
            account_external_id=DEFAULT_EXTERNAL_USER_ID,
            current_password="Temporal123",
            new_password=NewPassword("NuevaPasswordSegura2026"),
        )
    )

    assert ("fake-access-token-1804470738", True) in provider.signed_out_tokens


async def test_si_supabase_rechaza_el_cambio_se_cierra_la_sesion_de_verificacion() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    provider = FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
        change_password_error=WeakPassword(),
    )
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    repo = FakeUserAccountRepository([account])
    uow = FakeUnitOfWork()
    clock = FrozenClock(datetime(2026, 10, 4, 15, 0, tzinfo=UTC))

    use_case = ChangePassword(
        identity_provider=provider,
        accounts=repo,
        clock=clock,
        unit_of_work=uow,
        throttle=InMemorySignInThrottle(clock=clock),
    )

    with pytest.raises(WeakPassword):
        await use_case.execute(
            ChangePasswordCommand(
                account_external_id=DEFAULT_EXTERNAL_USER_ID,
                current_password="Temporal123",
                new_password=NewPassword("NuevaPasswordSegura2026"),
            )
        )

    assert ("fake-access-token-1804470738", False) in provider.signed_out_tokens
    assert not repo.password_changes
