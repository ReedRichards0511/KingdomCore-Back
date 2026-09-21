---
name: kingdom-back-use-cases
description: Patron para escribir casos de uso en la capa de aplicacion del backend Kingdom Core. Una clase, un execute(), transaccion explicita, auditoria obligatoria en operaciones sensibles. Usar al crear archivos en contexts/*/application/use_cases/.
---

# Kingdom Back — Casos de uso

Un caso de uso orquesta: pide datos a los puertos, deja que las entidades
decidan, persiste y registra la auditoria. No contiene reglas de negocio — esas
viven en el dominio.

## Forma

Una clase por caso de uso. Dependencias por constructor. Un unico metodo
publico `execute()`.

```python
# contexts/enrollment/application/use_cases/withdraw_student.py
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from kingdom.contexts.enrollment.domain.errors import EnrollmentNotFound
from kingdom.contexts.enrollment.domain.ports.enrollment_repository import (
    EnrollmentRepository,
)
from kingdom.shared.domain.ports.clock import Clock
from kingdom.shared.domain.ports.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class WithdrawStudentCommand:
    enrollment_id: UUID
    reason: str
    actor_id: UUID


class WithdrawStudent:
    def __init__(
        self,
        *,
        enrollments: EnrollmentRepository,
        charges: ChargeRepository,
        audit: AuditLog,
        clock: Clock,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._enrollments = enrollments
        self._charges = charges
        self._audit = audit
        self._clock = clock
        self._uow = unit_of_work

    async def execute(self, command: WithdrawStudentCommand) -> None:
        async with self._uow:
            enrollment = await self._enrollments.get(command.enrollment_id)
            if enrollment is None:
                raise EnrollmentNotFound(
                    "No existe la inscripcion",
                    enrollment_id=str(command.enrollment_id),
                )

            before = copy.deepcopy(enrollment)

            # La entidad protege su propia invariante.
            enrollment.withdraw(at=self._clock.now(), reason=command.reason)
            await self._enrollments.update(enrollment)

            # Los cargos pendientes se anulan; nunca se borran.
            await self._charges.cancel_pending_for_enrollment(
                enrollment.id,
                reason=f"Retiro del estudiante: {command.reason}",
                actor_id=command.actor_id,
            )

            await self._audit.record(
                table="enrollments",
                record_id=enrollment.id,
                action="update",
                actor_id=command.actor_id,
                before=before,
                after=enrollment,
            )
```

## Reglas

1. **Comando de entrada, no parametros sueltos.** Un `@dataclass(frozen=True)`
   con el sufijo `Command` o `Query`. Facilita agregar campos sin romper
   llamadas.
2. **Tipos del dominio, no DTOs.** El `Command` lleva `UUID`, `Decimal`,
   value objects. La conversion desde pydantic ocurre en el router.
3. **La transaccion se abre aqui,** no en el repositorio. Un caso de uso, una
   unidad de trabajo.
4. **Cero `if` de negocio.** Si aparece un `if enrollment.status == ...`, esa
   decision pertenece a la entidad.
5. **Sin `print` ni logging de negocio.** Los eventos importantes van al
   `audit_log`, no a la consola. Ruff bloquea `print` con la regla `T20`.
6. **El actor siempre viaja en el comando.** Toda escritura sensible necesita
   saber quien la hizo.

## Auditoria obligatoria

Estas operaciones **no** se pueden escribir sin registrar en `audit_log`:

- Registrar, ajustar o descontar un pago
- Anular cargos por retiro
- Proponer y confirmar una promocion
- Justificar una falta fuera de la ventana de 30 dias
- Fusionar familias
- Regenerar credenciales de un usuario
- Abrir o cerrar un anio lectivo

## Consultas

Las lecturas no necesitan transaccion ni entidades completas. Se permite un
caso de uso de lectura que devuelva una proyeccion plana:

```python
@dataclass(frozen=True, slots=True)
class GroupRosterRow:
    enrollment_id: UUID
    full_name: str
    attendance_rate: Decimal
    payment_status: PaymentStatus  # al dia | pendiente
    documents_complete: bool


class GetGroupRoster:
    """Lista del grupo con el semaforo que ve el catequista.

    El catequista ve el estado, nunca los montos ni los recibos.
    """

    async def execute(self, query: GetGroupRosterQuery) -> list[GroupRosterRow]: ...
```

La proyeccion vive en `application/`, no en `domain/`: no es una entidad, es
una vista armada para una pantalla.

## Nombres

Verbo en imperativo, en ingles, describiendo la intencion del negocio:

| Bien | Mal |
|---|---|
| `EnrollStudent` | `CreateEnrollment` |
| `WithdrawStudent` | `UpdateEnrollmentStatus` |
| `RegisterPayment` | `InsertPayment` |
| `ProposePromotion` | `SetPromotionFlag` |
| `ConfirmPromotion` | `UpdateReview` |
| `JustifyAbsence` | `PatchAttendance` |
| `RegenerateCredentials` | `ResetPassword` |
| `LinkSibling` | `UpdateFamily` |

## Anti-patrones

| Mal | Bien |
|---|---|
| Un `EnrollmentService` con doce metodos | Doce clases con un `execute()` |
| El caso de uso arma el SQL | El SQL vive en el repositorio |
| El caso de uso devuelve un modelo pydantic | Devuelve entidades o proyecciones |
| El caso de uso llama a `datetime.now()` | Pide la hora al puerto `Clock` |
| El caso de uso construye `uuid4()` | Pide el identificador a `IdGenerator` |
| Reglas de negocio repartidas en varios casos de uso | Regla unica dentro de la entidad |

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
