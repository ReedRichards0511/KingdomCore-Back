# Kingdom Core — Backend

API de gestión catequética para la Parroquia El Buen Pastor de Turubamba.
Arquitectura hexagonal, modular por contexto acotado.

## Antes de escribir código

Carga la skill que corresponda a lo que vas a tocar:

| Tarea | Skill |
|---|---|
| Cualquier archivo nuevo, ubicación, regla de dependencia | `kingdom-back-structure` |
| Entidades, value objects, errores de dominio | `kingdom-back-domain` |
| Puertos y cableado en el contenedor | `kingdom-back-ports` |
| Casos de uso | `kingdom-back-use-cases` |
| Repositorios sobre Postgres | `kingdom-back-adapters-postgres` |
| Routers y DTOs | `kingdom-back-adapters-http` |
| Autenticación, roles, cuentas | `kingdom-back-auth-supabase` |
| Pruebas | `kingdom-back-testing` |
| Migraciones y esquema | `kingdom-back-migrations` + `supabase-postgres-best-practices` |

## Reglas que no se negocian

1. **Sin triggers, sin funciones, sin RPC en Postgres.** Toda la lógica vive en Python.
   Único valor por defecto permitido en el esquema: `now()` en `created_at`.
2. **Sin SDK de Supabase.** Ni `supabase-py` ni nada equivalente. Postgres por `asyncpg`,
   Auth por REST con `httpx`, verificación de JWT local contra el JWKS.
3. **UUIDv7 generado en Python**, nunca en la base.
4. **Borrado lógico siempre** (`deleted_at`). Nunca se ejecuta `DELETE`.
5. **La regla de dependencia apunta hacia adentro.** `domain/` no importa fastapi,
   asyncpg, pydantic ni httpx.
6. **Nadie se autorregistra.** Las cuentas las crea el administrador de comunidad.
7. **Un año lectivo cerrado es de solo lectura.**
8. **Los pagos no se editan ni se borran**: se corrigen con un ajuste de signo contrario.
9. **La promoción se bloquea por saldo pendiente o documentos incompletos, sin excepción.**
10. **Todo `timestamptz`.** Presentación en `America/Guayaquil`. Prohibido `datetime.now()`
    sin zona: ruff lo bloquea con la regla `DTZ`.
11. **Sin comentarios en el código.** Ni de línea, ni de bloque, ni docstrings
    explicativos. El nombre del módulo, de la función y de la variable es lo único que
    explica. Única excepción: las directivas que lee el tooling (`# type: ignore`,
    `# noqa`).

## Comandos

```bash
uv sync
uv run fastapi dev src/kingdom/main.py
uv run ruff check --fix . && uv run ruff format .
uv run mypy src
uv run pytest -m "not integration"
uv run alembic upgrade head
```

## Estado

- Esqueleto y configuración: listos.
- Migraciones: pendientes. Se aplican una por una, con revisión previa.
- Credenciales de Supabase y Cloudinary: `POR_CONFIGURAR` en `.env`.
