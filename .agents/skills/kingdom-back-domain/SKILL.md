---
name: kingdom-back-domain
description: Patron para escribir entidades, value objects y errores de dominio en el backend Kingdom Core. Dataclasses puras sin framework, invariantes en el constructor, comportamiento dentro de la entidad. Usar al crear cualquier archivo bajo contexts/*/domain/.
---

# Kingdom Back — Capa de dominio

El dominio es el unico sitio donde viven las reglas del negocio catequetico.
No sabe que existe HTTP, ni Postgres, ni Supabase, ni pydantic.

## Prohibiciones

En cualquier archivo bajo `contexts/*/domain/`:

```python
import asyncpg          # NO
from pydantic import BaseModel   # NO
from fastapi import ...          # NO
import httpx                     # NO
from datetime import datetime    # SI, pero nunca datetime.now()
```

La hora se pide al puerto `Clock`. Los identificadores, al puerto
`IdGenerator`. Ambos llegan por parametro desde el caso de uso.

## Entidades

`dataclass` con `slots=True`. Los invariantes se validan en `__post_init__`.
El comportamiento vive en metodos de la entidad, no en el caso de uso.

```python
# contexts/enrollment/domain/entities/enrollment.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from kingdom.shared.domain.errors import BusinessRuleViolation


class EnrollmentStatus(StrEnum):
    PRE_REGISTERED = "pre_registered"
    REGISTERED = "registered"
    ACTIVE = "active"
    APPROVED = "approved"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
    TRANSFERRED = "transferred"


class EnrollmentSource(StrEnum):
    REGULAR = "regular"
    TRANSFER = "transfer"
    MIGRATION = "migration"


@dataclass(slots=True)
class Enrollment:
    id: UUID
    person_id: UUID
    group_id: UUID
    academic_year_id: UUID
    family_id: UUID
    representative_person_id: UUID
    status: EnrollmentStatus
    source: EnrollmentSource
    enrolled_at: datetime
    observations: str | None = None
    transfer_origin: str | None = None
    catechist_signed_by: UUID | None = None
    catechist_signed_at: date | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.source is EnrollmentSource.TRANSFER and not self.transfer_origin:
            raise BusinessRuleViolation(
                "Una inscripcion por traslado exige indicar la comunidad de origen",
                enrollment_id=str(self.id),
            )

    @property
    def is_closed(self) -> bool:
        return self.status in {
            EnrollmentStatus.APPROVED,
            EnrollmentStatus.FAILED,
            EnrollmentStatus.WITHDRAWN,
            EnrollmentStatus.TRANSFERRED,
        }

    def withdraw(self, *, at: datetime, reason: str) -> None:
        if self.is_closed:
            raise BusinessRuleViolation(
                "La inscripcion ya esta cerrada y no admite retiro",
                enrollment_id=str(self.id),
                status=self.status.value,
            )
        self.status = EnrollmentStatus.WITHDRAWN
        self.observations = reason
        self.deleted_at = None  # el retiro no borra: cambia de estado
```

Fijarse en el patron: `withdraw()` protege su propia invariante. El caso de
uso no pregunta `if enrollment.status == ...` antes de llamar; la entidad se
defiende sola.

## Value objects

Inmutables (`frozen=True`), se validan al construirse y no tienen identidad.

```python
# contexts/identity/domain/value_objects/national_id.py
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from kingdom.shared.domain.errors import ValidationError


class DocumentType(StrEnum):
    CEDULA = "cedula"
    PASAPORTE = "pasaporte"
    CARNE_REFUGIADO = "carne_refugiado"


@dataclass(frozen=True, slots=True)
class NationalId:
    document_type: DocumentType
    number: str

    def __post_init__(self) -> None:
        number = self.number.strip()
        if not number:
            raise ValidationError("El numero de documento no puede estar vacio")
        if self.document_type is DocumentType.CEDULA and not _is_valid_cedula(number):
            raise ValidationError(
                "La cedula ecuatoriana no pasa el digito verificador",
                number=number,
            )
        object.__setattr__(self, "number", number)

    @property
    def synthetic_email_local_part(self) -> str:
        """Parte local del correo sintetico que consume Supabase Auth."""
        return f"{self.document_type.value}-{self.number}"
```

Value objects que ya se sabe que hacen falta: `NationalId`, `FullName`
(con apellido paterno y materno separados, porque de ahi sale la deteccion de
hermanos), `Money`, `AttendanceRate`, `ReceiptNumber`, `DateRange`.

## Dinero

Nunca `float`. Siempre `Decimal` con dos decimales.

```python
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValidationError("Un monto no puede ser negativo")
        object.__setattr__(
            self, "amount", self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
```

## Errores

Los errores comunes estan en `kingdom.shared.domain.errors`. Cada contexto
agrega los suyos en `contexts/<ctx>/domain/errors.py`, siempre heredando de la
jerarquia compartida:

```python
from kingdom.shared.domain.errors import BusinessRuleViolation, NotFoundError


class EnrollmentNotFound(NotFoundError):
    code = "enrollment_not_found"


class PromotionBlocked(BusinessRuleViolation):
    """Saldo pendiente o documentacion incompleta impiden promover."""

    code = "promotion_blocked"
```

El `code` es lo que el frontend lee para decidir que mensaje mostrar. El
`context` del error lleva los datos que el frontend necesita para explicarlo:

```python
raise PromotionBlocked(
    "El estudiante tiene saldo pendiente",
    enrollment_id=str(enrollment.id),
    outstanding_balance=str(balance.amount),
)
```

## Reglas de negocio que viven en el dominio

| Regla | Donde |
|---|---|
| Asistido = presente, atraso o justificado | `AttendanceStatus.counts_as_present` |
| Denominador del porcentaje = solo sesiones `held` | `AttendanceRate.of()` |
| Alerta a las 3 faltas injustificadas (configurable) | `AttendanceSummary` |
| Justificacion dentro de la ventana (30 dias, configurable) | `AttendanceRecord.justify()` |
| Promocion bloqueada por saldo o documentos, **sin override** | `PromotionCandidate.evaluate()` |
| Un solo sobre compromiso por familia, comunidad y anio | `CommitmentEnvelopePolicy` |
| Un anio lectivo cerrado no se edita | `AcademicYear.assert_open()` |

Si una de estas reglas termina escrita dentro de un router o de un
repositorio, esta en el lugar equivocado.

## Sin comentarios en el codigo

No se escriben comentarios. Ni de linea, ni de bloque, ni docstrings
explicativos. El nombre del archivo, de la funcion y de la variable es lo unico
que explica que hace el codigo. Si un fragmento necesita un comentario para
entenderse, la respuesta es extraerlo a una funcion con nombre propio, no
anotarlo.

Unica excepcion: las directivas que leen las herramientas, porque no son
comentarios sino instrucciones al tooling.

```
# type: ignore[arg-type]
# noqa: E501
// eslint-disable-next-line react-hooks/exhaustive-deps
// @ts-expect-error
```

Los ejemplos de esta skill llevan una primera linea con la ruta del archivo
solo para situar el fragmento. El codigo real no la lleva.
