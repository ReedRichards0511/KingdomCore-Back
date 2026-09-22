from __future__ import annotations

import argparse
import asyncio
import secrets
import sys
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

import asyncpg
import httpx

from kingdom.platform.settings import Settings, get_settings
from kingdom.shared.infrastructure.clock import SystemClock
from kingdom.shared.infrastructure.id_generator import Uuid7Generator

TEMPORARY_PASSWORD_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TEMPORARY_PASSWORD_LENGTH = 10


class BootstrapError(Exception):
    pass


@dataclass(frozen=True)
class AdminData:
    document_type: str
    document_number: str
    first_names: str
    paternal_surname: str
    maternal_surname: str | None
    birth_date: date
    sex: str
    phone: str | None
    contact_email: str | None


def parse_arguments(argv: list[str]) -> AdminData:
    parser = argparse.ArgumentParser(prog="bootstrap_parish_admin")
    parser.add_argument(
        "--document-type", default="cedula", choices=["cedula", "passport", "refugee_id"]
    )
    parser.add_argument("--document-number", required=True)
    parser.add_argument("--first-names", required=True)
    parser.add_argument("--paternal-surname", required=True)
    parser.add_argument("--maternal-surname")
    parser.add_argument("--birth-date", required=True, type=date.fromisoformat)
    parser.add_argument("--sex", required=True, choices=["male", "female"])
    parser.add_argument("--phone")
    parser.add_argument("--contact-email")
    arguments = parser.parse_args(argv)
    return AdminData(
        document_type=arguments.document_type,
        document_number=arguments.document_number.strip(),
        first_names=arguments.first_names.strip(),
        paternal_surname=arguments.paternal_surname.strip(),
        maternal_surname=arguments.maternal_surname,
        birth_date=arguments.birth_date,
        sex=arguments.sex,
        phone=arguments.phone,
        contact_email=arguments.contact_email,
    )


def generate_temporary_password() -> str:
    return "".join(
        secrets.choice(TEMPORARY_PASSWORD_ALPHABET) for _ in range(TEMPORARY_PASSWORD_LENGTH)
    )


def admin_headers(settings: Settings) -> dict[str, str]:
    key = settings.supabase.service_role_key.get_secret_value()
    return {"apikey": key, "Authorization": f"Bearer {key}"}


async def find_single_parish(connection: asyncpg.Connection[Any]) -> UUID:
    rows = await connection.fetch("SELECT id FROM parishes WHERE deleted_at IS NULL")
    if len(rows) != 1:
        raise BootstrapError(f"Se esperaba exactamente una parroquia activa y hay {len(rows)}")
    parish_id: UUID = rows[0]["id"]
    return parish_id


async def ensure_person_is_new(connection: asyncpg.Connection[Any], admin: AdminData) -> None:
    existing = await connection.fetchval(
        "SELECT id FROM persons WHERE document_type = $1 AND document_number = $2",
        admin.document_type,
        admin.document_number,
    )
    if existing is not None:
        raise BootstrapError(f"Ya existe una persona con el documento {admin.document_number}")


async def create_auth_user(
    client: httpx.AsyncClient, settings: Settings, admin: AdminData, password: str
) -> UUID:
    response = await client.post(
        settings.supabase.admin_users_url,
        headers=admin_headers(settings),
        json={
            "email": f"{admin.document_number}@{settings.supabase.synthetic_email_domain}",
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "document_type": admin.document_type,
                "document_number": admin.document_number,
            },
        },
    )
    if response.status_code >= 400:
        raise BootstrapError(
            f"Supabase Auth rechazo la cuenta: {response.status_code} {response.text}"
        )
    return UUID(response.json()["id"])


async def remove_auth_user(
    client: httpx.AsyncClient, settings: Settings, external_user_id: UUID
) -> None:
    await client.delete(
        f"{settings.supabase.admin_users_url}/{external_user_id}",
        headers=admin_headers(settings),
    )


async def insert_admin_records(
    connection: asyncpg.Connection[Any], admin: AdminData, external_user_id: UUID, parish_id: UUID
) -> UUID:
    ids = Uuid7Generator()
    now = SystemClock().now()
    person_id = ids.generate()
    account_id = ids.generate()
    async with connection.transaction():
        await connection.execute(
            """
            INSERT INTO persons (
                id, document_type, document_number, first_names, paternal_surname,
                maternal_surname, birth_date, sex, phone, contact_email, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
            person_id,
            admin.document_type,
            admin.document_number,
            admin.first_names,
            admin.paternal_surname,
            admin.maternal_surname,
            admin.birth_date,
            admin.sex,
            admin.phone,
            admin.contact_email,
            now,
        )
        await connection.execute(
            """
            INSERT INTO user_accounts (
                id, person_id, external_user_id, is_active, must_change_password, created_at
            ) VALUES ($1, $2, $3, true, true, $4)
            """,
            account_id,
            person_id,
            external_user_id,
            now,
        )
        await connection.execute(
            """
            INSERT INTO role_assignments (
                id, user_account_id, role, scope_type, scope_id, created_at
            ) VALUES ($1, $2, 'parish_admin', 'parish', $3, $4)
            """,
            ids.generate(),
            account_id,
            parish_id,
            now,
        )
    return account_id


async def bootstrap(admin: AdminData) -> None:
    settings = get_settings()
    password = generate_temporary_password()
    connection = await asyncpg.connect(dsn=settings.database.url.get_secret_value())
    try:
        parish_id = await find_single_parish(connection)
        await ensure_person_is_new(connection, admin)
        async with httpx.AsyncClient(timeout=15.0) as client:
            external_user_id = await create_auth_user(client, settings, admin, password)
            try:
                account_id = await insert_admin_records(
                    connection, admin, external_user_id, parish_id
                )
            except Exception:
                await remove_auth_user(client, settings, external_user_id)
                raise
    finally:
        await connection.close()

    sys.stdout.write(
        "Administrador de parroquia creado.\n"
        f"  Cuenta:              {account_id}\n"
        f"  Usuario (documento): {admin.document_number}\n"
        f"  Contrasena temporal: {password}\n"
        "Se muestra una sola vez. Debe cambiarse en el primer ingreso.\n"
    )


def main() -> None:
    admin = parse_arguments(sys.argv[1:])
    try:
        asyncio.run(bootstrap(admin))
    except BootstrapError as error:
        sys.stderr.write(f"{error}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
