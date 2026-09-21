"""Jerarquia de errores de dominio.

Estos errores no conocen HTTP. La traduccion a codigos de estado vive en
``kingdom.shared.api.error_handlers``, que es el unico lugar del proyecto que
sabe que existe un protocolo web.
"""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Raiz de todo error de negocio."""

    code: str = "domain_error"

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class NotFoundError(DomainError):
    """El recurso solicitado no existe."""

    code = "not_found"


class ConflictError(DomainError):
    """La operacion choca con el estado actual del sistema."""

    code = "conflict"


class ValidationError(DomainError):
    """Los datos violan una regla de negocio."""

    code = "validation_error"


class BusinessRuleViolation(DomainError):
    """Una invariante del dominio impide continuar.

    Es el error de las reglas duras del proyecto: promover con saldo
    pendiente, justificar una falta fuera de la ventana, tocar un anio
    lectivo cerrado.
    """

    code = "business_rule_violation"


class PermissionDeniedError(DomainError):
    """El actor no tiene el rol o el ambito necesario."""

    code = "permission_denied"


class AuthenticationError(DomainError):
    """Credenciales ausentes, invalidas o expiradas."""

    code = "authentication_error"


class ExternalServiceError(DomainError):
    """Un proveedor externo fallo: Supabase Auth, Cloudinary."""

    code = "external_service_error"
