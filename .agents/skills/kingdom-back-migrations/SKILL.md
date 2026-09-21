---
name: kingdom-back-migrations
description: Convenciones de migracion SQL del backend Kingdom Core. Archivos .sql planos versionados, Alembic como libro de versiones, prohibicion de triggers y funciones, borrado logico, nombres de restricciones. Usar al crear o modificar cualquier migracion o tabla.
---

# Kingdom Back — Migraciones

El esquema se construye con archivos `.sql` planos. Alembic es solo el libro
que registra cual se aplico y en que orden.

## Estructura

```
migrations/
  env.py                 # configuracion de Alembic
  sql_loader.py          # read_sql() y run_sql()
  sql/
    0001_core_hierarchy.sql
    0002_persons_auth.sql
    ...
  versions/
    0001_core_hierarchy.py     # tres lineas: ejecuta el .sql
```

Cada revision de Alembic es una envoltura:

```python
revision = "0001"
down_revision = None


def upgrade() -> None:
    run_sql("0001_core_hierarchy.sql")


def downgrade() -> None:
    run_sql("0001_core_hierarchy.down.sql")
```

El SQL queda legible en el diff del pull request y se puede aplicar a mano
desde el panel de Supabase si hiciera falta.

## Orden de las migraciones

| # | Archivo | Contenido |
|---|---|---|
| 0001 | `core_hierarchy` | enums base, `media_assets`, jerarquia, `parish_settings` |
| 0002 | `persons_auth` | `persons`, `user_accounts`, `role_assignments` |
| 0003 | `families` | `families`, `family_members`, `family_merges` |
| 0004 | `levels` | `level_templates`, `parish_levels`, `community_levels` |
| 0005 | `academic_years` | `academic_years`, `community_academic_years` |
| 0006 | `groups_schedules` | `groups`, `group_schedules`, `group_catechists` |
| 0007 | `enrollments` | `enrollments`, documentos, `person_sacraments` |
| 0008 | `sessions_attendance` | `class_sessions`, `attendance_records` |
| 0009 | `billing` | `fee_types` … `receipt_counters` |
| 0010 | `promotions` | `promotion_reviews`, `level_certificates` |
| 0011 | `events_notifications` | eventos, audiencias, notificaciones |
| 0012 | `audit_assessments` | `audit_log`, `assessments`, `assessment_results` |
| 0013 | `seed_base_data` | jerarquia real, 6 niveles, tipos de cobro y evento |

## Prohibiciones absolutas

```sql
CREATE TRIGGER ...        -- NO
CREATE FUNCTION ...       -- NO
CREATE OR REPLACE RULE    -- NO
DEFAULT gen_random_uuid() -- NO: los identificadores nacen en Python
```

Toda la logica vive en el backend. El unico valor por defecto permitido es
`now()` en `created_at`.

Motivo: una funcion en la base no aparece en el diff de un pull request, no se
prueba con pytest y obliga a razonar en dos lugares a la vez.

## Convenciones de tabla

Cada tabla lleva estas columnas, en este orden, al final:

```sql
CREATE TABLE enrollments (
    id                 uuid PRIMARY KEY,
    -- ... columnas del negocio ...
    created_at         timestamptz NOT NULL DEFAULT now(),
    created_by         uuid REFERENCES user_accounts (id),
    updated_at         timestamptz,
    updated_by         uuid REFERENCES user_accounts (id),
    deleted_at         timestamptz
);
```

| Regla | Detalle |
|---|---|
| Nombres | `snake_case`, en **ingles**, tablas en plural |
| Identificadores | `uuid PRIMARY KEY`, sin `DEFAULT` |
| Tiempo | `timestamptz` siempre. `date` para fechas puras, `time` para horas del dia |
| Dinero | `numeric(10,2)` |
| Borrado | `deleted_at timestamptz`. Nunca `ON DELETE CASCADE` |
| Enums | nativos para maquinas de estado fijas; tabla catalogo para lo extensible |

## Restricciones con nombre

Toda restriccion lleva nombre explicito, porque el repositorio la distingue
por ese nombre al traducir el error a una excepcion de dominio.

```sql
ALTER TABLE persons
    ADD CONSTRAINT persons_document_unique
    UNIQUE (document_type, document_number);
```

## Indices unicos parciales

Son la herramienta que reemplaza a los triggers en este proyecto.

```sql
-- Un alumno, una inscripcion por anio lectivo
CREATE UNIQUE INDEX enrollments_one_per_year
    ON enrollments (person_id, academic_year_id)
    WHERE deleted_at IS NULL;

-- Un solo catequista titular vigente por grupo
CREATE UNIQUE INDEX group_catechists_single_lead
    ON group_catechists (group_id)
    WHERE role = 'lead' AND unassigned_at IS NULL;

-- Un solo ciclo abierto por comunidad
CREATE UNIQUE INDEX community_years_single_open
    ON community_academic_years (community_id)
    WHERE status <> 'closed';

-- Un solo sobre compromiso por familia, comunidad y anio
CREATE UNIQUE INDEX charges_one_envelope_per_family
    ON charges (family_id, community_id, academic_year_id, fee_type_id)
    WHERE family_id IS NOT NULL AND deleted_at IS NULL;
```

Lo que un indice parcial no puede expresar — por ejemplo "todo grupo activo
necesita al menos un titular" — lo valida el backend.

## Indices de consulta

Se crea indice para toda columna que aparezca en un `WHERE` o un `JOIN`
frecuente:

```sql
CREATE INDEX enrollments_by_group ON enrollments (group_id) WHERE deleted_at IS NULL;
CREATE INDEX attendance_by_enrollment ON attendance_records (enrollment_id);
CREATE INDEX persons_by_surnames ON persons (paternal_surname, maternal_surname);
CREATE INDEX audit_log_by_record ON audit_log (table_name, record_id);
```

`persons_by_surnames` es el que sostiene la deteccion de hermanos al
matricular.

## Flujo de trabajo

1. Escribir `migrations/sql/00NN_nombre.sql` y su `.down.sql`.
2. Crear la revision en `migrations/versions/` que lo ejecuta.
3. Revisar el SQL a ojo. Es la ultima oportunidad antes de que toque datos
   reales.
4. Aplicar con el MCP de Supabase o con `uv run alembic upgrade head`.
5. Confirmar con `uv run alembic current`.

Una migracion aplicada no se edita. Si algo salio mal, se corrige con una
migracion nueva.

## Antes de escribir SQL

Cargar tambien la skill `supabase-postgres-best-practices`, que cubre tipos de
columna, planes de consulta y trampas de rendimiento de Postgres.

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
