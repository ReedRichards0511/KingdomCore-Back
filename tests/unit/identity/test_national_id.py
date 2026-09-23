from __future__ import annotations

import pytest

from kingdom.contexts.identity.domain.value_objects.national_id import (
    DocumentType,
    NationalId,
)
from kingdom.shared.domain.errors import ValidationError


def test_la_cedula_del_administrador_es_valida() -> None:
    nid = NationalId(DocumentType.CEDULA, "1804470738")
    assert nid.number == "1804470738"
    assert nid.document_type is DocumentType.CEDULA


def test_una_cedula_con_digito_verificador_incorrecto_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        NationalId(DocumentType.CEDULA, "1804470739")


def test_una_cedula_de_provincia_inexistente_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        NationalId(DocumentType.CEDULA, "2504470738")


def test_un_pasaporte_no_pasa_por_el_digito_verificador() -> None:
    passport = NationalId(DocumentType.PASSPORT, "A12345678")
    assert passport.number == "A12345678"
    assert passport.document_type is DocumentType.PASSPORT
