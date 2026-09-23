from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from kingdom.contexts.identity.application.projections.account_profile import (
    AccountProfile,
    RoleView,
)
from kingdom.contexts.identity.application.use_cases.change_password import ChangePassword
from kingdom.contexts.identity.application.use_cases.get_account_profile import (
    GetAccountProfile,
)
from kingdom.contexts.identity.application.use_cases.refresh_session import RefreshSession
from kingdom.contexts.identity.application.use_cases.resolve_current_account import (
    ResolveCurrentAccount,
)
from kingdom.contexts.identity.application.use_cases.sign_in import SignIn
from kingdom.contexts.identity.domain.entities.user_account import UserAccount
from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.contexts.identity.domain.value_objects.role_assignment import RoleName
from kingdom.contexts.identity.domain.value_objects.token_claims import TokenClaims
from kingdom.contexts.identity.infrastructure.throttling.in_memory_sign_in_throttle import (
    InMemorySignInThrottle,
)
from kingdom.main import create_app
from kingdom.platform.container import build_container
from kingdom.shared.api.dependencies import require_role
from kingdom.shared.infrastructure.clock import FrozenClock
from tests.factories import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_EXTERNAL_USER_ID,
    DEFAULT_PARISH_ID,
    make_user_account,
)
from tests.fakes.identity import (
    FakeAccountProfileQuery,
    FakeIdentityProvider,
    FakeTokenVerifier,
    FakeUnitOfWork,
    FakeUserAccountRepository,
)


@pytest.fixture
def provider() -> FakeIdentityProvider:
    return FakeIdentityProvider(
        credentials={"1804470738": "Temporal123"},
        users_by_number={"1804470738": DEFAULT_EXTERNAL_USER_ID},
    )


@pytest.fixture
def accounts() -> FakeUserAccountRepository:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    account = make_user_account(
        national_id=nid,
        external_user_id=DEFAULT_EXTERNAL_USER_ID,
        must_change_password=True,
    )
    return FakeUserAccountRepository([account])


@pytest.fixture
def verifier() -> FakeTokenVerifier:
    return FakeTokenVerifier(
        claims_by_token={
            "fake-access-token-1804470738": TokenClaims(DEFAULT_EXTERNAL_USER_ID),
        }
    )


@pytest.fixture
def profiles() -> FakeAccountProfileQuery:
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
    return FakeAccountProfileQuery({DEFAULT_ACCOUNT_ID: profile})


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def throttle(clock: FrozenClock) -> InMemorySignInThrottle:
    return InMemorySignInThrottle(clock=clock, max_failures=5, window_seconds=900)


@pytest.fixture
def client(
    provider: FakeIdentityProvider,
    accounts: FakeUserAccountRepository,
    verifier: FakeTokenVerifier,
    profiles: FakeAccountProfileQuery,
    uow: FakeUnitOfWork,
    throttle: InMemorySignInThrottle,
    clock: FrozenClock,
) -> TestClient:
    app = create_app()

    @app.get("/test-protected")
    def _protected_route(
        _acc: Annotated[UserAccount, Depends(require_role(RoleName.PARISH_ADMIN))],
    ) -> dict[str, str]:
        return {"status": "ok"}

    container = build_container()
    container.wire(packages=["kingdom.contexts", "kingdom.shared.api"])
    app.state.container = container

    container.identity_provider.override(provider)
    container.token_verifier.override(verifier)
    container.sign_in_throttle.override(throttle)

    container.sign_in.override(
        SignIn(
            identity_provider=provider,
            accounts=accounts,
            clock=clock,
            unit_of_work=uow,
            throttle=throttle,
        )
    )
    container.refresh_session.override(
        RefreshSession(
            identity_provider=provider,
            accounts=accounts,
            unit_of_work=uow,
        )
    )
    container.change_password.override(
        ChangePassword(
            identity_provider=provider,
            accounts=accounts,
            clock=clock,
            unit_of_work=uow,
            throttle=throttle,
        )
    )
    container.resolve_current_account.override(
        ResolveCurrentAccount(
            token_verifier=verifier,
            accounts=accounts,
            unit_of_work=uow,
        )
    )
    container.get_account_profile.override(
        GetAccountProfile(
            profiles=profiles,
            unit_of_work=uow,
        )
    )

    return TestClient(app)


@pytest.fixture
def access_token(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "documentType": "cedula",
            "documentNumber": "1804470738",
            "password": "Temporal123",
        },
    )
    data = response.json()
    return data["accessToken"]  # type: ignore[no-any-return]
