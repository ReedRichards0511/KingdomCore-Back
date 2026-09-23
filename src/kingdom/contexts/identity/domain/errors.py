from __future__ import annotations

from typing import Any

from kingdom.shared.domain.errors import (
    AuthenticationError,
    PermissionDeniedError,
    TooManyRequestsError,
    ValidationError,
)


class InvalidCredentials(AuthenticationError):
    code = "invalid_credentials"

    def __init__(self, message: str = "Credenciales incorrectas", **context: Any) -> None:
        super().__init__(message, **context)


class InvalidToken(AuthenticationError):
    code = "invalid_token"

    def __init__(self, message: str = "Token invalido o expirado", **context: Any) -> None:
        super().__init__(message, **context)


class MissingToken(AuthenticationError):
    code = "missing_token"

    def __init__(
        self, message: str = "Token de autenticacion no proporcionado", **context: Any
    ) -> None:
        super().__init__(message, **context)


class AccountNotProvisioned(AuthenticationError):
    code = "account_not_provisioned"

    def __init__(
        self, message: str = "La cuenta no esta configurada en el sistema", **context: Any
    ) -> None:
        super().__init__(message, **context)


class AccountDisabled(AuthenticationError):
    code = "account_disabled"

    def __init__(self, message: str = "La cuenta se encuentra desactivada", **context: Any) -> None:
        super().__init__(message, **context)


class PasswordChangeRequired(PermissionDeniedError):
    code = "password_change_required"

    def __init__(
        self,
        message: str = "Es obligatorio cambiar la contrasena antes de continuar",
        **context: Any,
    ) -> None:
        super().__init__(message, **context)


class WeakPassword(ValidationError):
    code = "weak_password"

    def __init__(
        self, message: str = "La contrasena debe tener al menos 8 caracteres", **context: Any
    ) -> None:
        super().__init__(message, **context)


class PasswordReused(ValidationError):
    code = "password_reused"

    def __init__(
        self, message: str = "La nueva contrasena debe ser distinta a la actual", **context: Any
    ) -> None:
        super().__init__(message, **context)


class TooManySignInAttempts(TooManyRequestsError):
    code = "too_many_sign_in_attempts"

    def __init__(
        self,
        message: str = "Demasiados intentos fallidos. Intente de nuevo en unos minutos",
        **context: Any,
    ) -> None:
        super().__init__(message, **context)


class InvalidCurrentPassword(ValidationError):
    code = "invalid_current_password"

    def __init__(self, message: str = "La contrasena actual es incorrecta", **context: Any) -> None:
        super().__init__(message, **context)
