---
name: kingdom-back-adapters-http
description: Patron para routers FastAPI y DTOs pydantic en el backend Kingdom Core. Traduccion DTO-comando, inyeccion desde el contenedor, errores de dominio a codigos HTTP. Usar al crear archivos en contexts/*/api/.
---

# Kingdom Back — Adaptadores HTTP

El router es un traductor. Recibe JSON, lo convierte en un comando del
dominio, llama al caso de uso y convierte el resultado en JSON. Nada mas.

## Forma

```python
# contexts/enrollment/api/routers/enrollments.py
from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from kingdom.contexts.enrollment.api.schemas.enrollment import (
    EnrollStudentRequest,
    EnrollmentResponse,
)
from kingdom.contexts.enrollment.application.use_cases.enroll_student import (
    EnrollStudent,
    EnrollStudentCommand,
)
from kingdom.platform.container import Container
from kingdom.shared.api.dependencies import CurrentUser, require_role

router = APIRouter(prefix="/enrollments", tags=["inscripciones"])


@router.post(
    "",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscribe a un estudiante en un grupo",
)
@inject
async def enroll_student(
    payload: EnrollStudentRequest,
    current_user: CurrentUser = Depends(require_role("community_admin")),
    use_case: EnrollStudent = Depends(Provide[Container.enroll_student]),
) -> EnrollmentResponse:
    enrollment = await use_case.execute(
        EnrollStudentCommand(
            person_id=payload.person_id,
            group_id=payload.group_id,
            representative_person_id=payload.representative_person_id,
            family_id=payload.family_id,
            source=payload.source,
            transfer_origin=payload.transfer_origin,
            actor_id=current_user.id,
        )
    )
    return EnrollmentResponse.from_entity(enrollment)
```

## Reglas

1. **El router no tiene logica.** Traduce, delega, traduce de vuelta. Si tiene
   un `if` que decide algo del negocio, ese `if` pertenece al dominio.
2. **El router no toca la base de datos.** Ni una linea de SQL, ni un
   `connection`.
3. **El actor sale del token,** nunca del cuerpo de la peticion. Un cliente no
   declara quien es.
4. **Los errores no se capturan aqui.** `DomainError` sube y lo traduce
   `shared/api/error_handlers.py`. Nada de `try/except HTTPException`.
5. **Un `response_model` explicito** en cada endpoint.
6. **Verbos correctos:** `POST` crea, `PATCH` modifica parcialmente, `PUT`
   reemplaza, `GET` lee. Nada de `POST /get-enrollments`.

## DTOs

Viven en `api/schemas/`. Son pydantic y **no cruzan hacia adentro**: un caso
de uso jamas recibe un `BaseModel`.

```python
# contexts/enrollment/api/schemas/enrollment.py
from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from kingdom.contexts.enrollment.domain.entities.enrollment import (
    Enrollment,
    EnrollmentSource,
)


class EnrollStudentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    group_id: UUID
    representative_person_id: UUID
    family_id: UUID
    source: EnrollmentSource = EnrollmentSource.REGULAR
    transfer_origin: str | None = Field(default=None, max_length=200)


class EnrollmentResponse(BaseModel):
    id: UUID
    person_id: UUID
    group_id: UUID
    status: str
    enrolled_at: datetime

    @classmethod
    def from_entity(cls, entity: Enrollment) -> Self:
        return cls(
            id=entity.id,
            person_id=entity.person_id,
            group_id=entity.group_id,
            status=entity.status.value,
            enrolled_at=entity.enrolled_at,
        )
```

`extra="forbid"` en todas las peticiones: si el frontend manda un campo que no
existe, es un error, no algo que se ignora en silencio.

## Forma de los errores

El manejador central responde siempre con la misma estructura, para que el
frontend tenga un solo camino de manejo:

```json
{
  "error": {
    "code": "promotion_blocked",
    "message": "El estudiante tiene saldo pendiente",
    "details": { "enrollment_id": "...", "outstanding_balance": "15.00" }
  }
}
```

| Error de dominio | HTTP |
|---|---|
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ValidationError`, `BusinessRuleViolation` | 422 |
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403 |
| `ExternalServiceError` | 502 |

## Montaje

Cada contexto expone un router agregado en `api/routers/__init__.py`, y
`platform/router.py` los monta todos bajo `/api/v1`:

```python
# contexts/enrollment/api/routers/__init__.py
from fastapi import APIRouter

from .documents import router as documents_router
from .enrollments import router as enrollments_router

enrollment_router = APIRouter()
enrollment_router.include_router(enrollments_router)
enrollment_router.include_router(documents_router)
```

## Descarga de archivos

La ficha de inscripcion y los recibos se devuelven como PDF generado por
WeasyPrint:

```python
@router.get("/{enrollment_id}/ficha.pdf")
async def download_enrollment_sheet(...) -> Response:
    pdf = await use_case.execute(RenderEnrollmentSheetQuery(enrollment_id))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="ficha-{enrollment_id}.pdf"'
        },
    )
```

## Anti-patrones

| Mal | Bien |
|---|---|
| El router arma SQL | El SQL vive en el repositorio |
| `try: ... except DomainError: raise HTTPException` | Dejar subir; lo traduce el manejador central |
| El caso de uso recibe el `BaseModel` | El router construye el `Command` |
| `actor_id` viene en el cuerpo | `actor_id` sale del token |
| `POST /enrollments/list` | `GET /enrollments` |
| Endpoint sin `response_model` | Siempre declarado |
