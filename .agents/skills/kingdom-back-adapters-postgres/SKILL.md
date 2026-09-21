---
name: kingdom-back-adapters-postgres
description: Patron para repositorios sobre asyncpg con SQL escrito a mano en el backend Kingdom Core. Mapeo fila-entidad, borrado logico, parametros posicionales, sin ORM. Usar al crear archivos en contexts/*/infrastructure/repositories/.
---

# Kingdom Back — Repositorios Postgres

Sin ORM. SQL escrito a mano sobre `asyncpg`. Cada repositorio implementa un
puerto del dominio y traduce entre filas y entidades.

## Forma

```python
# contexts/enrollment/infrastructure/repositories/enrollment_repository.py
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from kingdom.contexts.enrollment.domain.entities.enrollment import (
    Enrollment,
    EnrollmentSource,
    EnrollmentStatus,
)

if TYPE_CHECKING:
    import asyncpg

    from kingdom.shared.domain.ports.unit_of_work import UnitOfWork

_COLUMNS = """
    id, person_id, group_id, academic_year_id, family_id,
    representative_person_id, status, source, transfer_origin,
    observations, catechist_signed_by, catechist_signed_at,
    enrolled_at, deleted_at
"""


class PostgresEnrollmentRepository:
    def __init__(self, *, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def get(self, enrollment_id: UUID) -> Enrollment | None:
        row = await self._uow.connection.fetchrow(
            f"SELECT {_COLUMNS} FROM enrollments WHERE id = $1 AND deleted_at IS NULL",
            enrollment_id,
        )
        return _to_entity(row) if row else None

    async def find_active_for_year(
        self, person_id: UUID, academic_year_id: UUID
    ) -> Enrollment | None:
        row = await self._uow.connection.fetchrow(
            f"""
            SELECT {_COLUMNS}
              FROM enrollments
             WHERE person_id = $1
               AND academic_year_id = $2
               AND deleted_at IS NULL
            """,
            person_id,
            academic_year_id,
        )
        return _to_entity(row) if row else None

    async def add(self, enrollment: Enrollment) -> None:
        await self._uow.connection.execute(
            """
            INSERT INTO enrollments (
                id, person_id, group_id, academic_year_id, family_id,
                representative_person_id, status, source, transfer_origin,
                observations, enrolled_at, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
            enrollment.id,
            enrollment.person_id,
            enrollment.group_id,
            enrollment.academic_year_id,
            enrollment.family_id,
            enrollment.representative_person_id,
            enrollment.status.value,
            enrollment.source.value,
            enrollment.transfer_origin,
            enrollment.observations,
            enrollment.enrolled_at,
            enrollment.created_by,
        )


def _to_entity(row: asyncpg.Record) -> Enrollment:
    return Enrollment(
        id=row["id"],
        person_id=row["person_id"],
        group_id=row["group_id"],
        academic_year_id=row["academic_year_id"],
        family_id=row["family_id"],
        representative_person_id=row["representative_person_id"],
        status=EnrollmentStatus(row["status"]),
        source=EnrollmentSource(row["source"]),
        transfer_origin=row["transfer_origin"],
        observations=row["observations"],
        catechist_signed_by=row["catechist_signed_by"],
        catechist_signed_at=row["catechist_signed_at"],
        enrolled_at=row["enrolled_at"],
        deleted_at=row["deleted_at"],
    )
```

## Reglas

1. **Parametros posicionales `$1, $2`.** Nunca interpolacion de cadenas con
   datos. La unica interpolacion permitida es la de constantes controladas por
   el codigo, como `_COLUMNS`.
2. **Todo `SELECT` filtra `deleted_at IS NULL`.** Si un listado debe incluir
   los borrados, el metodo se llama distinto y lo dice:
   `list_including_deleted`.
3. **Nunca se ejecuta `DELETE`.** El borrado es
   `UPDATE ... SET deleted_at = $n`.
4. **La funcion de mapeo es privada y esta al final del modulo.**
   `_to_entity(row)`. Un repositorio, un mapeo.
5. **Los enums se guardan por `.value`** y se reconstruyen con
   `EnumClase(row["columna"])`.
6. **La conexion sale de la unidad de trabajo,** nunca del pool directamente.
   Asi el caso de uso controla la transaccion.
7. **El repositorio no valida reglas de negocio.** Si un `INSERT` viola una
   restriccion, se traduce la excepcion de asyncpg a un error de dominio.

## Traducir errores de Postgres

```python
import asyncpg

from kingdom.contexts.identity.domain.errors import DuplicateNationalId

try:
    await self._uow.connection.execute(sql, *args)
except asyncpg.UniqueViolationError as exc:
    if exc.constraint_name == "persons_document_unique":
        raise DuplicateNationalId(
            "Ya existe una persona con ese documento",
            document_number=national_id.number,
        ) from exc
    raise
```

Cada restriccion de la base tiene nombre explicito en la migracion,
precisamente para poder distinguirla aqui.

## Consultas de lectura con proyeccion

Cuando la pantalla necesita datos de varias tablas, el repositorio devuelve la
proyeccion de `application/`, no una entidad a medio llenar:

```python
    async def group_roster(self, group_id: UUID) -> list[GroupRosterRow]:
        rows = await self._uow.connection.fetch(
            """
            SELECT e.id AS enrollment_id,
                   p.first_names || ' ' || p.paternal_surname || ' ' || p.maternal_surname
                       AS full_name,
                   COALESCE(a.rate, 0) AS attendance_rate,
                   NOT EXISTS (
                       SELECT 1 FROM charges c
                        WHERE c.enrollment_id = e.id
                          AND c.status <> 'paid'
                          AND c.deleted_at IS NULL
                   ) AS is_up_to_date
              FROM enrollments e
              JOIN persons p ON p.id = e.person_id
              LEFT JOIN attendance_rates a ON a.enrollment_id = e.id
             WHERE e.group_id = $1
               AND e.deleted_at IS NULL
             ORDER BY p.paternal_surname, p.maternal_surname, p.first_names
            """,
            group_id,
        )
        return [_to_roster_row(row) for row in rows]
```

Ordenar por `paternal_surname, maternal_surname, first_names` es la convencion
del proyecto para cualquier listado de personas: es como estan ordenadas las
carpetas de papel.

## Rendimiento

- Traer solo las columnas necesarias. `SELECT *` no se usa.
- Un `fetch` que devuelve N filas y luego N consultas por fila es el error
  clasico: resolver con `JOIN` o con `WHERE id = ANY($1::uuid[])`.
- Insercion masiva (por ejemplo, generar las sesiones del anio o precargar la
  asistencia de un grupo): `executemany` o `UNNEST`.

```python
async def add_many(self, sessions: list[ClassSession]) -> None:
    await self._uow.connection.executemany(
        "INSERT INTO class_sessions (id, group_id, session_date, ...) VALUES ($1, $2, $3, ...)",
        [(s.id, s.group_id, s.session_date, ...) for s in sessions],
    )
```

## Anti-patrones

| Mal | Bien |
|---|---|
| `f"WHERE id = '{user_input}'"` | `"WHERE id = $1", user_input` |
| `SELECT *` | Lista explicita de columnas |
| `DELETE FROM ...` | `UPDATE ... SET deleted_at = $1` |
| Repositorio que abre su propia transaccion | La transaccion la abre el caso de uso |
| Repositorio que devuelve `asyncpg.Record` | Devuelve entidades o proyecciones |
| Repositorio que decide si se puede promover | Esa decision es del dominio |
| Llamar a una funcion de Postgres | No existen funciones en este esquema |
