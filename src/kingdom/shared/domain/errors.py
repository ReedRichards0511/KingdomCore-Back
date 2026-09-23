from __future__ import annotations

from typing import Any


class DomainError(Exception):
    code: str = "domain_error"

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class ValidationError(DomainError):
    code = "validation_error"


class BusinessRuleViolation(DomainError):
    code = "business_rule_violation"


class PermissionDeniedError(DomainError):
    code = "permission_denied"


class AuthenticationError(DomainError):
    code = "authentication_error"


class ExternalServiceError(DomainError):
    code = "external_service_error"


class TooManyRequestsError(DomainError):
    code = "too_many_requests"
