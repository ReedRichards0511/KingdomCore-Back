from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kingdom.shared.domain.errors import ValidationError


class DocumentType(StrEnum):
    CEDULA = "cedula"
    PASSPORT = "passport"
    REFUGEE_ID = "refugee_id"


def _is_valid_cedula(number: str) -> bool:
    if len(number) != 10 or not number.isdigit():
        return False

    province = int(number[:2])
    if not ((1 <= province <= 24) or province == 30):
        return False

    third_digit = int(number[2])
    if third_digit >= 6:
        return False

    coefficients = (2, 1, 2, 1, 2, 1, 2, 1, 2)
    total = 0
    for digit_char, coef in zip(number[:9], coefficients, strict=True):
        product = int(digit_char) * coef
        if product > 9:
            product -= 9
        total += product

    verifier = (10 - (total % 10)) % 10
    return verifier == int(number[9])


@dataclass(frozen=True, slots=True)
class NationalId:
    document_type: DocumentType
    number: str

    def __post_init__(self) -> None:
        cleaned = self.number.strip()
        object.__setattr__(self, "number", cleaned)

        if not cleaned:
            raise ValidationError("El numero de documento no puede estar vacio")

        if self.document_type is DocumentType.CEDULA and not _is_valid_cedula(cleaned):
            raise ValidationError("La cedula ingresada no es valida")
