"""Traduccion de errores de dominio a respuestas HTTP.

Este modulo es la frontera: es el unico sitio donde un error de negocio se
convierte en un codigo de estado. Ningun caso de uso ni entidad debe importar
``fastapi`` para reportar un fallo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse

from kingdom.shared.domain.errors import (
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainError,
    ExternalServiceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from kingdom.shared.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from fastapi.responses import Response

logger = get_logger(__name__)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    BusinessRuleViolation: status.HTTP_422_UNPROCESSABLE_CONTENT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
}


def _status_for(error: DomainError) -> int:
    for error_type, http_status in STATUS_BY_ERROR.items():
        if isinstance(error, error_type):
            return http_status
    return status.HTTP_400_BAD_REQUEST


async def domain_error_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, DomainError)
    http_status = _status_for(exc)

    logger.warning(
        "domain_error",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
        status=http_status,
        **exc.context,
    )

    return ORJSONResponse(
        status_code=http_status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.context or None,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
