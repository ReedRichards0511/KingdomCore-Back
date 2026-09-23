from __future__ import annotations

from fastapi.testclient import TestClient

from tests.factories import DEFAULT_ACCOUNT_ID


def test_el_login_con_contrasena_incorrecta_responde_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "documentType": "cedula",
            "documentNumber": "1804470738",
            "password": "WrongPassword",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_el_login_responde_en_camel_case(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "documentType": "cedula",
            "documentNumber": "1804470738",
            "password": "Temporal123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert "expiresIn" in data
    assert "mustChangePassword" in data
    assert data["mustChangePassword"] is True


def test_me_sin_token_responde_missing_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_token"


def test_me_devuelve_el_rol_y_el_nombre_del_ambito(client: TestClient, access_token: str) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["accountId"] == str(DEFAULT_ACCOUNT_ID)
    assert data["documentNumber"] == "1804470738"
    assert data["roles"][0]["role"] == "parish_admin"
    assert data["roles"][0]["scopeName"] == "Parroquia El Buen Pastor"


def test_con_contrasena_temporal_un_endpoint_protegido_responde_403(
    client: TestClient, access_token: str
) -> None:
    response = client.get("/test-protected", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "password_change_required"


def test_la_contrasena_actual_incorrecta_responde_422(
    client: TestClient, access_token: str
) -> None:
    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "currentPassword": "IncorrectPassword123",
            "newPassword": "NuevaPasswordValida123",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_current_password"


def test_tras_cambiar_la_contrasena_el_endpoint_protegido_responde_200(
    client: TestClient, access_token: str
) -> None:
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "currentPassword": "Temporal123",
            "newPassword": "NuevaPasswordValida123",
        },
    )
    assert change_res.status_code == 200
    new_token = change_res.json()["accessToken"]

    response = client.get("/test-protected", headers={"Authorization": f"Bearer {new_token}"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_el_sexto_intento_fallido_responde_429(client: TestClient) -> None:
    for _ in range(5):
        res = client.post(
            "/api/v1/auth/login",
            json={
                "documentType": "cedula",
                "documentNumber": "1804470738",
                "password": "WrongPassword",
            },
        )
        assert res.status_code == 401

    res = client.post(
        "/api/v1/auth/login",
        json={
            "documentType": "cedula",
            "documentNumber": "1804470738",
            "password": "WrongPassword",
        },
    )
    assert res.status_code == 429
    assert res.headers["Retry-After"] == "900"
    assert res.json()["error"]["code"] == "too_many_sign_in_attempts"
    assert res.json()["error"]["details"]["retryAfterSeconds"] == 900


def test_una_peticion_con_campos_extra_se_rechaza(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "documentType": "cedula",
            "documentNumber": "1804470738",
            "password": "Temporal123",
            "extraField": "unexpected_field",
        },
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"]["fields"] == ["extraField"]


def test_el_error_de_validacion_no_devuelve_la_contrasena(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"documentType": "cedula", "password": "Secreta123"},
    )
    assert response.status_code == 422
    assert "Secreta123" not in response.text
    assert response.json()["error"]["details"]["fields"] == ["documentNumber"]
