---
name: kingdom-back-auth-supabase
description: Integracion con Supabase Auth sin SDK en el backend Kingdom Core. Login por cedula con correo sintetico, verificacion local de JWT contra JWKS, Admin API por REST, roles y ambitos. Usar al tocar autenticacion, autorizacion o creacion de cuentas.
---

# Kingdom Back — Autenticacion con Supabase, sin SDK

Supabase cumple dos papeles en este proyecto y ninguno mas: **Postgres
alojado** y **proveedor de identidad**. Esta prohibido instalar `supabase-py`
o cualquier SDK. Se habla con Supabase por HTTP, como con cualquier API
externa.

## Login por cedula

El usuario nunca ve un correo. Teclea su **cedula** y su contrasena.

```
cedula 1712345678  ──►  backend  ──►  1712345678@buenpastor.app  ──►  Supabase Auth
```

El dominio del correo sintetico sale de `SUPABASE_SYNTHETIC_EMAIL_DOMAIN`. La
traduccion vive en el adaptador, nunca en el dominio ni en el router.

Si la persona tiene correo real, se guarda en `persons.contact_email` como
dato informativo. No es el identificador de acceso.

## Los tres canales

| Canal | Como | Cuando |
|---|---|---|
| Datos | `asyncpg` directo a Postgres | Toda lectura y escritura del negocio |
| Cuentas | REST al Admin API con `httpx` | Crear usuario, regenerar contrasena, desactivar |
| Token | Verificacion local contra JWKS | En cada peticion |

## Crear una cuenta

Solo el administrador de comunidad crea cuentas. Nadie se autorregistra.

```python
# contexts/identity/infrastructure/supabase/auth_provider.py
import secrets

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from kingdom.shared.domain.errors import ExternalServiceError


class SupabaseAuthProvider:
    def __init__(self, *, settings: SupabaseSettings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
    async def provision_account(self, national_id: NationalId) -> ProvisionedAccount:
        password = _generate_temporary_password()
        email = f"{national_id.number}@{self._settings.synthetic_email_domain}"

        response = await self._client.post(
            self._settings.admin_users_url,
            headers=self._admin_headers(),
            json={
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "document_type": national_id.document_type.value,
                    "document_number": national_id.number,
                },
            },
        )
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Supabase Auth rechazo la creacion de la cuenta",
                status=response.status_code,
            )

        return ProvisionedAccount(
            external_user_id=UUID(response.json()["id"]),
            temporary_password=password,
        )

    def _admin_headers(self) -> dict[str, str]:
        key = self._settings.service_role_key.get_secret_value()
        return {"apikey": key, "Authorization": f"Bearer {key}"}


def _generate_temporary_password() -> str:
    """Contrasena temporal legible, para dictarla o imprimirla."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin caracteres ambiguos
    return "".join(secrets.choice(alphabet) for _ in range(10))
```

## Regla dura sobre la contrasena temporal

La contrasena temporal **se muestra una sola vez**, cuando se crea la cuenta.
El sistema no la guarda en claro en ningun lado: Supabase almacena solo el
hash y nosotros no duplicamos nada.

Si el representante pierde el papel, el administrador usa **regenerar
credenciales**, que produce una contrasena nueva y deja registro en
`audit_log` de quien la regenero y cuando.

La cuenta nace con `must_change_password = true` en `user_accounts`. Mientras
esa bandera este activa, el backend responde `403` con el codigo
`password_change_required` a todo endpoint que no sea el de cambio de
contrasena.

## Verificar el token

Sin llamar a Supabase en cada peticion: se cachea el JWKS.

```python
import jwt
from jwt import PyJWKClient

from kingdom.shared.domain.errors import AuthenticationError


class SupabaseTokenVerifier:
    def __init__(self, *, settings: SupabaseSettings) -> None:
        self._settings = settings
        self._jwks = PyJWKClient(
            settings.jwks_url,
            cache_keys=True,
            lifespan=settings.jwks_cache_seconds,
        )

    def verify(self, token: str) -> TokenClaims:
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.issuer,
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Token invalido o expirado") from exc

        return TokenClaims(external_user_id=UUID(payload["sub"]))
```

**Los roles no salen del token.** El token solo dice *quien* es. El *que
puede hacer* se resuelve consultando `user_accounts` y `role_assignments` en
cada peticion, porque un rol revocado debe surtir efecto de inmediato, sin
esperar a que el token expire.

## Roles y ambitos

```python
ROLES = {
    "archdiocese_admin",
    "vicariate_admin",
    "parish_admin",
    "community_admin",
    "catechist",
    "representative",
    "catechumen",
}
```

Un rol siempre viene con un **ambito**: `scope_type` (`parish` o `community`)
y `scope_id`. Ser `community_admin` de San Juan de Turubamba no da ningun
permiso sobre otra comunidad.

```python
def require_role(*roles: str) -> Callable[..., Awaitable[CurrentUser]]:
    async def dependency(
        token: str = Depends(bearer_scheme),
        accounts: AccountRepository = Depends(Provide[Container.account_repository]),
    ) -> CurrentUser:
        claims = verifier.verify(token)
        account = await accounts.get_by_external_id(claims.external_user_id)

        if account is None or not account.is_active:
            raise AuthenticationError("La cuenta no existe o esta desactivada")
        if account.must_change_password:
            raise PasswordChangeRequired("Debe cambiar su contrasena temporal")
        if not account.has_any_role(roles):
            raise PermissionDeniedError(
                "El usuario no tiene el rol necesario", required=list(roles)
            )
        return CurrentUser.from_account(account)

    return dependency
```

Verificar el ambito, no solo el rol: un endpoint que toca una comunidad debe
comprobar que el `scope_id` del rol coincide con la comunidad de la peticion.

## Quien puede que

| Accion | Rol |
|---|---|
| Crear comunidades, niveles, tarifario | `parish_admin` |
| Habilitar niveles, crear cuentas, inscribir, cobrar, eventos | `community_admin` |
| Abrir y cerrar el ciclo de su comunidad | `community_admin` |
| Crear sesiones, tomar asistencia, proponer promocion | `catechist` |
| Ver a sus representados | `representative` (solo lectura) |

El catequista ve un **semaforo** de pagos y documentos por alumno, nunca
montos ni recibos.

## Seguridad

- La `service_role` key vive solo en variables de entorno del backend. **Jamas
  llega al navegador ni se commitea.**
- Mientras RLS este desactivada en el proyecto de Supabase, la `anon` key no
  puede aparecer en el frontend. El frontend habla unicamente con esta API.
- Nunca registrar en logs el token, la contrasena temporal ni la
  `service_role` key.

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
