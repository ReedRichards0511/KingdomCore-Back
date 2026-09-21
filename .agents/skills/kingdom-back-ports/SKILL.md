---
name: kingdom-back-ports
description: Como declarar puertos (Protocols) en el dominio del backend Kingdom Core y cablearlos en el contenedor de dependency-injector. Usar al crear archivos en contexts/*/domain/ports/ o al registrar un adaptador nuevo.
---

# Kingdom Back — Puertos

Un puerto es una interfaz que el dominio declara y la infraestructura
implementa. Es el mecanismo que mantiene el hexagono cerrado: el dominio dice
**que** necesita, nunca **como** se consigue.

## Forma

`typing.Protocol`, no clase base abstracta. El adaptador no hereda de nada —
basta con que tenga los metodos, y mypy lo verifica en el punto de cableado.

```python
# contexts/enrollment/domain/ports/enrollment_repository.py
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from kingdom.contexts.enrollment.domain.entities.enrollment import Enrollment


class EnrollmentRepository(Protocol):
    async def get(self, enrollment_id: UUID) -> Enrollment | None: ...

    async def find_active_for_year(
        self, person_id: UUID, academic_year_id: UUID
    ) -> Enrollment | None: ...

    async def list_by_group(self, group_id: UUID) -> list[Enrollment]: ...

    async def add(self, enrollment: Enrollment) -> None: ...

    async def update(self, enrollment: Enrollment) -> None: ...
```

## Reglas

1. **El puerto habla el idioma del dominio.** Recibe y devuelve entidades y
   value objects, nunca filas, diccionarios ni DTOs de pydantic.
2. **Sin `save()` generico.** Los metodos nombran la intencion:
   `find_active_for_year`, `list_unpaid_charges`, `mark_as_delivered`.
3. **Sin filtros genericos.** Nada de `find(**kwargs)`. Cada consulta que el
   negocio necesita es un metodo con nombre propio.
4. **Sin paginacion inventada.** Si un listado la necesita, se declara
   explicita: `list_by_group(group_id, *, limit: int, offset: int)`.
5. **Devolver `None`, no lanzar.** El puerto reporta ausencia con `None`; es
   el caso de uso quien decide si eso amerita un `NotFoundError`.

## Puertos transversales

Ya existen en `kingdom.shared.domain.ports`:

| Puerto | Para que |
|---|---|
| `Clock` | Toda lectura de la hora. Permite probar ventanas y cierres |
| `IdGenerator` | UUIDv7. La base no genera identificadores |
| `UnitOfWork` | Transaccion con alcance de caso de uso |

## Puertos hacia servicios externos

Supabase Auth, Cloudinary y el renderizador de PDF tambien entran por puerto.
El dominio no sabe que existe ninguno de los tres.

```python
# contexts/identity/domain/ports/auth_provider.py
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from kingdom.contexts.identity.domain.value_objects.national_id import NationalId


class ProvisionedAccount(Protocol):
    external_user_id: UUID
    temporary_password: str


class AuthProvider(Protocol):
    """Creacion y mantenimiento de cuentas en el proveedor de identidad."""

    async def provision_account(self, national_id: NationalId) -> ProvisionedAccount: ...

    async def regenerate_password(self, external_user_id: UUID) -> str: ...

    async def disable_account(self, external_user_id: UUID) -> None: ...
```

El adaptador que habla REST con Supabase vive en
`contexts/identity/infrastructure/supabase/`. El dia que se cambie de
proveedor, el dominio no se entera.

## Cableado

Todo se declara en `platform/container.py`. Es el unico archivo que conoce a
la vez el puerto y su implementacion.

```python
class Container(containers.DeclarativeContainer):
    ...
    enrollment_repository = providers.Factory(
        PostgresEnrollmentRepository,
        unit_of_work=unit_of_work,
    )

    enroll_student = providers.Factory(
        EnrollStudent,
        enrollments=enrollment_repository,
        charges=charge_repository,
        clock=clock,
        ids=id_generator,
        unit_of_work=unit_of_work,
    )
```

`Factory`, no `Singleton`, para todo lo que toque una transaccion: cada
peticion abre la suya.

## Como verificar que un adaptador cumple su puerto

mypy lo comprueba solo en el contenedor. Para tenerlo explicito en el propio
adaptador:

```python
if TYPE_CHECKING:
    _: EnrollmentRepository = cast(PostgresEnrollmentRepository, None)
```

O, mas simple, una prueba de una linea:

```python
def test_el_repositorio_cumple_el_puerto() -> None:
    repo: EnrollmentRepository = PostgresEnrollmentRepository(unit_of_work=fake_uow)
    assert repo is not None
```

## Anti-patrones

| Mal | Bien |
|---|---|
| `async def save(self, data: dict)` | `async def add(self, enrollment: Enrollment)` |
| Puerto que devuelve `asyncpg.Record` | Puerto que devuelve `Enrollment` |
| Puerto con `session: AsyncSession` en la firma | La transaccion entra por `UnitOfWork` |
| Un `IRepository[T]` generico para todo | Un puerto por agregado, con metodos con nombre |
| Puerto declarado en `infrastructure/` | Puerto declarado en `domain/ports/` |

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
