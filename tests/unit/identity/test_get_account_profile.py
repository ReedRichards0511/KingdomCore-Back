from __future__ import annotations

from uuid import UUID

import pytest
from tests.factories import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_PARISH_ID,
)
from tests.fakes.identity import FakeAccountProfileQuery, FakeUnitOfWork

from kingdom.contexts.identity.application.projections.account_profile import (
    AccountProfile,
    RoleView,
)
from kingdom.contexts.identity.application.use_cases.get_account_profile import (
    GetAccountProfile,
    GetAccountProfileQuery,
)
from kingdom.shared.domain.errors import NotFoundError


async def test_obtener_perfil_existente() -> None:
    profile = AccountProfile(
        account_id=DEFAULT_ACCOUNT_ID,
        document_type="cedula",
        document_number="1804470738",
        first_names="Mauricio",
        paternal_surname="Alvarez",
        maternal_surname=None,
        contact_email="mauricio@example.com",
        must_change_password=True,
        roles=(
            RoleView(
                role="parish_admin",
                scope_type="parish",
                scope_id=DEFAULT_PARISH_ID,
                scope_name="Parroquia El Buen Pastor",
            ),
        ),
    )
    query_mock = FakeAccountProfileQuery({DEFAULT_ACCOUNT_ID: profile})
    uow = FakeUnitOfWork()
    use_case = GetAccountProfile(profiles=query_mock, unit_of_work=uow)

    result = await use_case.execute(GetAccountProfileQuery(account_id=DEFAULT_ACCOUNT_ID))

    assert result.account_id == DEFAULT_ACCOUNT_ID
    assert result.document_number == "1804470738"
    assert len(result.roles) == 1
    assert result.roles[0].scope_name == "Parroquia El Buen Pastor"
    assert uow.committed is True


async def test_obtener_perfil_inexistente_lanza_not_found() -> None:
    query_mock = FakeAccountProfileQuery()
    uow = FakeUnitOfWork()
    use_case = GetAccountProfile(profiles=query_mock, unit_of_work=uow)

    with pytest.raises(NotFoundError):
        await use_case.execute(
            GetAccountProfileQuery(account_id=UUID("00000000-0000-0000-0000-000000000000"))
        )
