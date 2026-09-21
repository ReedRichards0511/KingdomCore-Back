---
name: kingdom-back-testing
description: Patrones de prueba con pytest para el backend Kingdom Core. Fakes de puertos en unitarias, testcontainers en integracion, reloj congelado, nombres en espanol. Usar al escribir cualquier archivo en tests/.
---

# Kingdom Back — Pruebas

Tres niveles, con reglas distintas cada uno.

| Nivel | Que prueba | Dependencias reales |
|---|---|---|
| Unitaria | Entidades, value objects, casos de uso | Ninguna. Todo es fake |
| Integracion | Repositorios contra Postgres | Base de datos real en Docker |
| API | Endpoints de punta a punta | App completa, adaptadores falsos |

## Unitarias

Rapidas y sin red. Los puertos se sustituyen por fakes en memoria, nunca por
`unittest.mock.Mock`: un fake que se comporta es mucho mas util que un mock
que solo registra llamadas.

```python
# tests/unit/enrollment/test_withdraw_student.py
import pytest

from kingdom.contexts.enrollment.application.use_cases.withdraw_student import (
    WithdrawStudent,
    WithdrawStudentCommand,
)
from kingdom.contexts.enrollment.domain.entities.enrollment import EnrollmentStatus
from kingdom.shared.domain.errors import BusinessRuleViolation
from tests.fakes import FakeAuditLog, FakeChargeRepository, FakeEnrollmentRepository, FakeUnitOfWork


async def test_el_retiro_anula_los_cargos_pendientes(clock, ids) -> None:
    enrollment = make_enrollment(status=EnrollmentStatus.ACTIVE)
    enrollments = FakeEnrollmentRepository([enrollment])
    charges = FakeChargeRepository([make_charge(enrollment.id, amount="15.00")])

    use_case = WithdrawStudent(
        enrollments=enrollments,
        charges=charges,
        audit=FakeAuditLog(),
        clock=clock,
        unit_of_work=FakeUnitOfWork(),
    )

    await use_case.execute(
        WithdrawStudentCommand(
            enrollment_id=enrollment.id,
            reason="Cambio de domicilio",
            actor_id=ids.generate(),
        )
    )

    assert enrollments.get_sync(enrollment.id).status is EnrollmentStatus.WITHDRAWN
    assert charges.all_cancelled()
    assert charges.none_deleted(), "los cargos se anulan, no se borran"


async def test_no_se_puede_retirar_una_inscripcion_ya_cerrada(clock, ids) -> None:
    enrollment = make_enrollment(status=EnrollmentStatus.APPROVED)
    use_case = WithdrawStudent(...)

    with pytest.raises(BusinessRuleViolation):
        await use_case.execute(WithdrawStudentCommand(...))
```

## Fakes

Viven en `tests/fakes/`. Un fake por puerto, con estado en memoria y algun
metodo de inspeccion para las aserciones.

```python
class FakeEnrollmentRepository:
    def __init__(self, seed: list[Enrollment] | None = None) -> None:
        self._items = {e.id: e for e in (seed or [])}

    async def get(self, enrollment_id: UUID) -> Enrollment | None:
        return self._items.get(enrollment_id)

    async def add(self, enrollment: Enrollment) -> None:
        self._items[enrollment.id] = enrollment

    async def update(self, enrollment: Enrollment) -> None:
        self._items[enrollment.id] = enrollment

    # --- solo para las pruebas ---
    def get_sync(self, enrollment_id: UUID) -> Enrollment:
        return self._items[enrollment_id]
```

## Tiempo

Nunca se prueba contra el reloj real. La fixture `clock` de `conftest.py`
devuelve un `FrozenClock` detenido en un domingo del ciclo 2026-2027.

```python
async def test_la_falta_no_se_justifica_pasada_la_ventana(clock) -> None:
    record = make_attendance_record(session_date=date(2026, 10, 4))
    clock.advance(days=31)

    with pytest.raises(JustificationWindowClosed):
        record.justify(at=clock.now(), note="Certificado medico", window_days=30)
```

Los identificadores tambien son deterministas: la fixture `ids` entrega un
`SequentialIdGenerator`.

## Integracion

Solo para repositorios. Postgres real, porque el valor de la prueba esta en
comprobar el SQL de verdad: las restricciones, los indices unicos parciales y
el comportamiento del borrado logico.

```python
import pytest

pytestmark = pytest.mark.integration


async def test_un_alumno_no_puede_tener_dos_inscripciones_en_el_mismo_anio(
    repository, sample_person, academic_year
) -> None:
    await repository.add(make_enrollment(person_id=sample_person.id, year=academic_year.id))

    with pytest.raises(DuplicateEnrollment):
        await repository.add(make_enrollment(person_id=sample_person.id, year=academic_year.id))
```

Se marcan con `@pytest.mark.integration` y se excluyen del ciclo rapido:

```bash
uv run pytest -m "not integration"   # rapido, sin Docker
uv run pytest                        # todo
```

La base de prueba se levanta con `testcontainers` y se migra aplicando los
`.sql` de `migrations/sql/` en orden — el mismo esquema que produccion.

## Que se prueba siempre

Las reglas duras del proyecto necesitan prueba propia:

- Asistido = presente, atraso o justificado; ausente no cuenta
- El denominador del porcentaje solo incluye sesiones `held`
- La alerta salta a las 3 faltas injustificadas, y el umbral es configurable
- La justificacion falla pasados los 30 dias para el catequista
- La promocion se bloquea con saldo pendiente **y no hay override**
- La promocion se bloquea con documentos pendientes
- Un solo sobre compromiso por familia, comunidad y anio lectivo
- Dos hermanos en comunidades distintas generan **dos** sobres
- Un anio lectivo cerrado rechaza toda escritura
- Un pago no se puede editar ni borrar; solo se ajusta
- El numero de recibo no se repite bajo concurrencia

## Convenciones

- Nombres de prueba en **espanol**, en forma de afirmacion:
  `test_el_retiro_anula_los_cargos_pendientes`.
- Una asercion conceptual por prueba. Varias lineas de `assert` sobre el mismo
  hecho estan bien.
- `asyncio_mode = "auto"`: no hace falta decorar con `@pytest.mark.asyncio`.
- Constructores de datos en `tests/factories.py`: `make_enrollment()`,
  `make_charge()`, con valores por defecto sensatos y sobreescritura por
  palabra clave.

## Anti-patrones

| Mal | Bien |
|---|---|
| `Mock()` con `assert_called_once_with` | Fake con estado y aserciones sobre el estado |
| Prueba unitaria que toca Postgres | Fakes; si necesita la base, es de integracion |
| `datetime.now()` dentro de la prueba | La fixture `clock` |
| `uuid4()` dentro de la prueba | La fixture `ids` |
| Probar que el repositorio "llama al SQL" | Probar el efecto sobre la base real |
| Una prueba gigante que cubre todo el flujo | Una prueba por regla |
