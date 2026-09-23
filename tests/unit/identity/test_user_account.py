from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.factories import make_user_account

from kingdom.contexts.identity.domain.errors import (
    AccountDisabled,
    PasswordChangeRequired,
)
from kingdom.contexts.identity.domain.value_objects.role_assignment import RoleName
from kingdom.shared.domain.errors import PermissionDeniedError


def test_una_cuenta_desactivada_no_puede_iniciar_sesion() -> None:
    account = make_user_account(is_active=False)
    with pytest.raises(AccountDisabled):
        account.ensure_can_sign_in()


def test_con_contrasena_temporal_se_exige_cambiarla() -> None:
    account = make_user_account(must_change_password=True)
    with pytest.raises(PasswordChangeRequired):
        account.ensure_password_is_current()


def test_sin_el_rol_requerido_se_niega_el_permiso() -> None:
    account = make_user_account()
    with pytest.raises(PermissionDeniedError):
        account.ensure_has_any_role(frozenset({RoleName.ARCHDIOCESE_ADMIN}))


def test_completar_el_cambio_apaga_la_bandera() -> None:
    account = make_user_account(must_change_password=True)
    now = datetime(2026, 10, 4, 15, 30, tzinfo=UTC)

    account.complete_password_change(at=now)

    assert account.must_change_password is False
    assert account.updated_at == now
