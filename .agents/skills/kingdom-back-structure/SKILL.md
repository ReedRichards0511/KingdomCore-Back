---
name: kingdom-back-structure
description: Arquitectura hexagonal modular por contexto para el backend Kingdom Core (FastAPI + asyncpg + Supabase). Regla de dependencia, ubicacion de cada archivo y decisiones cerradas del proyecto. Usar antes de crear cualquier archivo nuevo en el backend.
---

# Kingdom Back — Estructura y regla de dependencia

Backend de gestion catequetica para la Parroquia El Buen Pastor de Turubamba.
Arquitectura **hexagonal (puertos y adaptadores)**, modular por **contexto acotado**.

## Stack cerrado

| Capa | Tecnologia |
|---|---|
| Lenguaje | Python 3.13 |
| Framework HTTP | FastAPI |
| Base de datos | PostgreSQL alojado en Supabase |
| Acceso a datos | `asyncpg` con **SQL escrito a mano**. Sin ORM |
| Migraciones | Alembic como libro de versiones sobre archivos `.sql` planos |
| Autenticacion | Supabase Auth por REST. **Sin SDK de Supabase, jamas** |
| Archivos | Cloudinary |
| PDF | WeasyPrint + Jinja2 |
| DI | `dependency-injector` |
| Paquetes | `uv` |
| Calidad | ruff, mypy estricto, pytest |

## La regla

> Las dependencias apuntan **hacia adentro**. El dominio no conoce a nadie.

```
api  ──────►  application  ──────►  domain  ◄────── infrastructure
```

`infrastructure` apunta al dominio porque **implementa sus puertos**. Nunca al reves.

| Capa | Puede importar | Jamas importa |
|---|---|---|
| `domain/` | `shared.domain`, stdlib | fastapi, asyncpg, pydantic, httpx, cloudinary |
| `application/` | su `domain`, `shared` | fastapi, asyncpg, httpx |
| `infrastructure/` | su `domain`, su `application`, librerias externas | otro contexto |
| `api/` | su `application`, su `domain`, fastapi, pydantic | asyncpg, SQL |

Si un archivo de `domain/` tiene un `import asyncpg` o un `from pydantic import`,
esta mal ubicado. No se negocia.

## Arbol

```
src/kingdom/
  main.py                    # create_app()
  shared/                    # kernel comun entre contextos
    domain/
      errors.py              # DomainError y su jerarquia
      ports/                 # clock, id_generator, unit_of_work
    infrastructure/
      clock.py               # SystemClock, FrozenClock
      id_generator.py        # Uuid7Generator, SequentialIdGenerator
      database/              # pool asyncpg, PostgresUnitOfWork
      storage/               # adaptador Cloudinary
      pdf/                   # renderizador WeasyPrint
      logging.py             # structlog
    api/
      error_handlers.py      # DomainError -> codigo HTTP
  contexts/
    identity/                # personas, cuentas, roles, familias
    catalog/                 # jerarquia eclesial, niveles, anios lectivos
    enrollment/              # inscripciones, documentos, sacramentos, promociones
    attendance/              # grupos, horarios, sesiones, asistencia
    billing/                 # tarifario, cargos, pagos, recibos
    communication/           # eventos, notificaciones
  platform/
    settings.py              # configuracion desde variables de entorno
    container.py             # raiz de composicion (DI)
    lifespan.py              # arranque y apagado
    router.py                # monta los routers de cada contexto en /api/v1
    middleware/
migrations/
  env.py                     # Alembic
  sql/                       # 0001_*.sql ... 0013_*.sql
  versions/                  # revisiones que solo ejecutan el .sql
templates/pdf/               # plantillas Jinja2 de la ficha y los recibos
tests/{unit,integration}/
```

## Anatomia de un contexto

Todos los contextos tienen exactamente la misma forma:

```
contexts/<contexto>/
  domain/
    entities/         # dataclasses puras
    value_objects/    # inmutables auto-validados
    ports/            # Protocols que la infraestructura implementa
    errors.py         # errores propios del contexto
  application/
    use_cases/        # una clase por caso de uso, con execute()
  infrastructure/
    repositories/     # implementaciones asyncpg con SQL a mano
  api/
    routers/          # endpoints FastAPI
    schemas/          # DTOs pydantic
```

## Comunicacion entre contextos

Un contexto **no importa** entidades ni repositorios de otro. Si `enrollment`
necesita saber si una persona existe, declara un puerto propio
(`PersonLookup`) y en el contenedor se cablea con un adaptador que llama al
caso de uso de `identity`.

Esto evita que `enrollment` y `identity` se fundan en una sola bola de barro
cuando el proyecto crezca a las otras comunidades de la parroquia.

## Decisiones que no se rediscuten

1. **Cero triggers, cero funciones, cero RPC en Postgres.** Toda la logica de
   negocio vive en Python. Unico valor por defecto permitido en el esquema:
   `now()` en `created_at`.
2. **UUIDv7 generado en Python** con `uuid_utils`, nunca en la base.
3. **Borrado logico siempre.** `deleted_at`. Nunca se ejecuta `DELETE`.
4. **Supabase es Postgres alojado + proveedor de autenticacion.** Nada mas.
   Prohibido `supabase-py`, `supabase-js` o cualquier SDK.
5. **Nadie se autorregistra.** Las cuentas las crea el administrador de
   comunidad.
6. **Los anios lectivos cerrados son de solo lectura.**
7. **Todo timestamp es `timestamptz`.** Zona de presentacion:
   `America/Guayaquil`. Prohibido `datetime.now()` sin zona — ruff lo bloquea
   con la regla `DTZ`.

## Comandos

```bash
uv sync                                  # instalar dependencias
uv run fastapi dev src/kingdom/main.py   # servidor de desarrollo
uv run ruff check --fix . && uv run ruff format .
uv run mypy src
uv run pytest
uv run alembic upgrade head
```

## Skills hermanas

| Tarea | Skill |
|---|---|
| Entidades y value objects | `kingdom-back-domain` |
| Definir un puerto | `kingdom-back-ports` |
| Escribir un caso de uso | `kingdom-back-use-cases` |
| Repositorio sobre Postgres | `kingdom-back-adapters-postgres` |
| Router y DTOs | `kingdom-back-adapters-http` |
| Autenticacion y roles | `kingdom-back-auth-supabase` |
| Pruebas | `kingdom-back-testing` |
| Migraciones SQL | `kingdom-back-migrations` |
