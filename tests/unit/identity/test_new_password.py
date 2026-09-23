from __future__ import annotations

import pytest

from kingdom.contexts.identity.domain.errors import WeakPassword
from kingdom.contexts.identity.domain.value_objects.password import NewPassword


def test_una_contrasena_de_menos_de_ocho_caracteres_se_rechaza() -> None:
    with pytest.raises(WeakPassword):
        NewPassword("1234567")


def test_la_contrasena_no_aparece_en_su_repr() -> None:
    pwd = NewPassword("MiClaveSegura123")
    assert "MiClaveSegura123" not in repr(pwd)
    assert "***" in repr(pwd)
