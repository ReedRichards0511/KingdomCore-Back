from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response, status

from kingdom.contexts.identity.api.schemas.auth import (
    ChangePasswordRequest,
    ProfileResponse,
    RefreshRequest,
    RoleResponse,
    SessionResponse,
    SignInRequest,
)
from kingdom.contexts.identity.application.use_cases.change_password import (
    ChangePassword,
    ChangePasswordCommand,
)
from kingdom.contexts.identity.application.use_cases.get_account_profile import (
    GetAccountProfile,
    GetAccountProfileQuery,
)
from kingdom.contexts.identity.application.use_cases.refresh_session import (
    RefreshSession,
    RefreshSessionCommand,
)
from kingdom.contexts.identity.application.use_cases.sign_in import (
    SignIn,
    SignInCommand,
)
from kingdom.contexts.identity.domain.entities.user_account import UserAccount
from kingdom.contexts.identity.domain.ports.identity_provider import IdentityProvider
from kingdom.contexts.identity.domain.value_objects.national_id import NationalId
from kingdom.contexts.identity.domain.value_objects.password import NewPassword
from kingdom.platform.container import Container
from kingdom.shared.api.dependencies import current_account, get_raw_token

router = APIRouter(prefix="/auth", tags=["autenticacion"])


@router.post("/login", response_model=SessionResponse, status_code=status.HTTP_200_OK)
@inject
async def login(
    request: SignInRequest,
    sign_in: SignIn = Depends(Provide[Container.sign_in]),
) -> SessionResponse:
    national_id = NationalId(request.document_type, request.document_number)
    result = await sign_in.execute(
        SignInCommand(
            national_id=national_id,
            password=request.password.get_secret_value(),
        )
    )
    return SessionResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        expires_in=result.session.expires_in,
        must_change_password=result.must_change_password,
    )


@router.post("/refresh", response_model=SessionResponse, status_code=status.HTTP_200_OK)
@inject
async def refresh(
    request: RefreshRequest,
    refresh_session: RefreshSession = Depends(Provide[Container.refresh_session]),
) -> SessionResponse:
    result = await refresh_session.execute(
        RefreshSessionCommand(refresh_token=request.refresh_token)
    )
    return SessionResponse(
        access_token=result.session.access_token,
        refresh_token=result.session.refresh_token,
        expires_in=result.session.expires_in,
        must_change_password=result.must_change_password,
    )


@router.post(
    "/change-password",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
)
@inject
async def change_password_endpoint(
    request: ChangePasswordRequest,
    account: UserAccount = Depends(current_account),
    change_password_use_case: ChangePassword = Depends(Provide[Container.change_password]),
) -> SessionResponse:
    new_password = NewPassword(request.new_password.get_secret_value())
    new_session = await change_password_use_case.execute(
        ChangePasswordCommand(
            account_external_id=account.external_user_id,
            current_password=request.current_password.get_secret_value(),
            new_password=new_password,
        )
    )
    return SessionResponse(
        access_token=new_session.access_token,
        refresh_token=new_session.refresh_token,
        expires_in=new_session.expires_in,
        must_change_password=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def logout(
    _account: UserAccount = Depends(current_account),
    token: str = Depends(get_raw_token),
    identity_provider: IdentityProvider = Depends(Provide[Container.identity_provider]),
) -> Response:
    await identity_provider.sign_out(token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
@inject
async def me(
    account: UserAccount = Depends(current_account),
    get_profile: GetAccountProfile = Depends(Provide[Container.get_account_profile]),
) -> ProfileResponse:
    profile = await get_profile.execute(GetAccountProfileQuery(account_id=account.id))
    return ProfileResponse(
        account_id=profile.account_id,
        document_type=profile.document_type,
        document_number=profile.document_number,
        first_names=profile.first_names,
        paternal_surname=profile.paternal_surname,
        maternal_surname=profile.maternal_surname,
        contact_email=profile.contact_email,
        must_change_password=profile.must_change_password,
        roles=[
            RoleResponse(
                role=r.role,
                scope_type=r.scope_type,
                scope_id=r.scope_id,
                scope_name=r.scope_name,
            )
            for r in profile.roles
        ],
    )
