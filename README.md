# Kingdom Core — Backend

API de gestión catequética para la **Parroquia Eclesiástica El Buen Pastor de Turubamba**.

Sustituye el registro en papel de inscripciones, asistencias, tareas, cobros y promociones de
nivel por un sistema con histórico consultable.

## Stack

| Área | Tecnología |
|---|---|
| Lenguaje | Python 3.13 |
| Framework | FastAPI |
| Base de datos | PostgreSQL (alojado en Supabase) |
| Acceso a datos | asyncpg con SQL escrito a mano |
| Migraciones | Alembic sobre archivos `.sql` versionados |
| Autenticación | Supabase Auth vía REST — **sin SDK** |
| Archivos | Cloudinary |
| PDF | WeasyPrint + Jinja2 |
| Inyección de dependencias | dependency-injector |
| Gestor de paquetes | uv |
| Calidad | ruff, mypy (estricto), pytest |

## Arquitectura

Hexagonal (puertos y adaptadores), modular por contexto acotado. La regla es una sola:

> Las dependencias apuntan **hacia adentro**. El dominio no conoce a nadie.

```
src/kingdom/
  shared/         # kernel compartido: errores, tipos, reloj, generador de ids
  contexts/       # un hexágono por contexto acotado
    identity/     #   personas, cuentas, roles, familias
    catalog/      #   jerarquía eclesial, niveles, años lectivos
    enrollment/   #   inscripciones, documentos, sacramentos, promociones
    attendance/   #   grupos, horarios, sesiones, asistencia
    billing/      #   tarifario, cargos, pagos, recibos
    communication/#   eventos, notificaciones
  platform/       # composición: contenedor DI, settings, middleware, ciclo de vida
```

Cada contexto se divide en cuatro capas:

| Capa | Contiene | Puede importar |
|---|---|---|
| `domain/` | Entidades, value objects, errores, **puertos** | Solo `shared` y la stdlib |
| `application/` | Casos de uso | `domain` |
| `infrastructure/` | Repositorios Postgres, clientes externos | `domain`, `application` |
| `api/` | Routers, DTOs, dependencias HTTP | `application`, `domain` |

## Reglas de base de datos

Innegociables en este proyecto:

- **Sin triggers, sin funciones, sin RPC.** Toda la lógica vive en el backend.
- Único valor por defecto permitido en el esquema: `now()` en `created_at`.
- Identificadores UUIDv7 generados en Python, no en Postgres.
- Borrado lógico en todas las tablas: `deleted_at`. Nunca `DELETE`.
- Supabase se usa solo como Postgres alojado y proveedor de autenticación.

## Puesta en marcha

```bash
uv sync
```

Copiar `.env.example` a `.env` y completar las credenciales.

```bash
uv run fastapi dev src/kingdom/main.py
```

### Comandos

| Comando | Qué hace |
|---|---|
| `uv sync` | Instala dependencias desde `uv.lock` |
| `uv run fastapi dev src/kingdom/main.py` | Servidor de desarrollo con recarga |
| `uv run ruff check --fix .` | Lint |
| `uv run ruff format .` | Formato |
| `uv run mypy src` | Tipos |
| `uv run pytest` | Pruebas |
| `uv run alembic upgrade head` | Aplica migraciones |

### WeasyPrint en Windows

WeasyPrint necesita el runtime **GTK3**, que no se instala con `uv sync`. Descargar e instalar
una sola vez desde [el instalador de GTK3 para Windows](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
En Linux y en el contenedor de despliegue no hace falta.

## Repositorio hermano

El frontend vive en `kingdom-core` (Vite + React Router + HeroUI).
