import pytest
from fastapi import HTTPException, Request
from fastapi.routing import APIRoute
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.testclient import TestClient
from google.oauth2 import id_token

from app.main import app
from app.security.auth import (
    require_user_login,
    require_user_api_access,
    require_internal_or_user_api_access,
)
from app.security.internal_access import require_internal_access

client = TestClient(app)


def test_all_internal_routes_are_protected_structurally():
    """
    Weryfikuje, czy każda zarejestrowana ścieżka zaczynająca się od /internal
    posiada wstrzykniętą przynajmniej jedną wymaganą zależność autoryzacyjną.
    Gwarantuje to, że zasada "Secure by Default" zdefiniowana na ruterach działa.
    """
    unprotected_routes = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        if not route.path.startswith("/internal"):
            continue

        has_auth = False
        for dep in route.dependencies:
            if dep.dependency in (
                require_user_login,
                require_user_api_access,
                require_internal_or_user_api_access,
                require_internal_access,
            ):
                has_auth = True
                break

        if not has_auth:
            methods = ",".join(route.methods or set())
            unprotected_routes.append(f"{methods} {route.path}")

    assert not unprotected_routes, f"Znaleziono niezabezpieczone endpointy wewnętrzne: {unprotected_routes}"


def test_internal_endpoints_functional_auth_rejection():
    """
    Funkcjonalny test wyrywkowy. Zastępuje mechanizm weryfikacji wymuszeniem błędu HTTP 401.
    """

    def mock_unauthorized():
        raise HTTPException(status_code=401, detail="Mocked Auth Reject")

    app.dependency_overrides[require_user_login] = mock_unauthorized
    app.dependency_overrides[require_user_api_access] = mock_unauthorized
    app.dependency_overrides[require_internal_or_user_api_access] = mock_unauthorized
    app.dependency_overrides[require_internal_access] = mock_unauthorized

    endpoints = [
        ("GET", "/internal/audit/jobs"),
        ("GET", "/internal/audit/companies"),
        ("POST", "/internal/discovery/run"),
        ("POST", "/internal/backfill-salary"),
        ("GET", "/internal/metrics"),
        ("POST", "/internal/tasks/tick"),
    ]

    try:
        for method, path in endpoints:
            response = client.request(method, path)
            assert response.status_code == 401, f"Endpoint {method} {path} nie został zabezpieczony!"
            assert response.json()["detail"] == "Mocked Auth Reject"
    finally:
        app.dependency_overrides.clear()


def test_require_internal_access_with_valid_oidc(monkeypatch):
    """Testuje czy poprawny token OIDC autoryzuje żądanie z zewnątrz."""

    # 1. Zmockuj weryfikację tokenu przez bibliotekę Google
    def mock_verify_oauth2_token(token, request, audience=None):
        if token == "valid-mock-token":
            return {"email": "scheduler-internal@example.com"}
        raise ValueError("Invalid token signature")

    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify_oauth2_token)
    monkeypatch.setenv("SCHEDULER_SA_EMAIL", "scheduler-internal@example.com")

    # 2. Skonstruuj fałszywy obiekt żądania (pochodzący spoza localhost/testclient)
    scope = {
        "type": "http",
        "client": ("198.51.100.1", 12345),  # Zewnętrzny adres IP
        "headers": [(b"authorization", b"Bearer valid-mock-token")],
    }
    request = Request(scope)

    # 3. Jeśli token jest prawidłowy, funkcja nie powinna rzucić wyjątku
    assert require_internal_access(request) is None


def test_require_internal_access_unauthorized_email_oidc(monkeypatch):
    """Testuje czy poprawny token, ale nieuprawniony e-mail zostanie odrzucony."""

    def mock_verify_oauth2_token(token, request, audience=None):
        return {"email": "hacker@evil.com"}

    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify_oauth2_token)
    monkeypatch.setenv("SCHEDULER_SA_EMAIL", "scheduler-internal@example.com")
    monkeypatch.setenv("ALLOWED_AUTH_EMAIL", "admin@example.com")

    scope = {
        "type": "http",
        "client": ("198.51.100.1", 12345),
        "headers": [(b"authorization", b"Bearer valid-mock-token")],
    }
    request = Request(scope)

    # Oczekujemy, że FastAPI rzuci wyjątek autoryzacji
    with pytest.raises(HTTPException) as exc:
        require_internal_access(request)

    assert exc.value.status_code == 401


def test_all_endpoints_have_tags():
    """
    Weryfikuje, czy każdy zarejestrowany w aplikacji endpoint ma przypisany przynajmniej jeden tag.
    Metoda dynamiczna doskonale radzi sobie z tagami odziedziczonymi z instancji APIRouter.
    """
    untagged_routes = []

    # Endpointy techniczne i autoryzacyjne, które celowo nie posiadają tagów
    allowed_untagged = {"/login", "/auth", "/logout", "/health", "/ready"}

    for route in app.routes:
        if isinstance(route, APIRoute):
            if not route.tags and route.path not in allowed_untagged:
                methods = ",".join(route.methods or set())
                untagged_routes.append(f"{methods} {route.path}")

    assert not untagged_routes, f"Znaleziono endpointy bez przypisanych tagów: {untagged_routes}"


def test_all_api_endpoints_have_response_model():
    """
    Weryfikuje, czy wszystkie standardowe endpointy API mają przypisany kontrakt Pydantic
    poprzez argument `response_model`.
    """
    missing_models = []

    # Lista endpointów, które świadomie nie zwracają ustrukturyzowanych danych JSON
    allowed_missing = {
        "/health",
        "/ready",
        "/login",
        "/logout",
        "/auth",
        "/internal/audit",  # Zwraca widok HTML
        "/internal/audit/script.js",  # Zwraca skrypt JS
        "/internal/audit/style.css",  # Zwraca arkusz CSS
        "/internal/audit/tick-dev",  # Zwraca Response z tekstem
        "/internal/preview-job",  # Zwraca Response (konsolowy output w przeglądarce)
        "/internal/audit/ats-force-sync/{company_ats_id}",  # Zwraca surowy Response
    }

    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path in allowed_missing:
                continue

            # Jeśli endpoint jawnie i z założenia zwraca HTML/Plik/Przekierowanie, ignorujemy go
            if route.response_class and isinstance(route.response_class, type):
                if issubclass(route.response_class, (HTMLResponse, FileResponse, RedirectResponse)):
                    continue

            if not route.response_model:
                methods = ",".join(route.methods or set())
                missing_models.append(f"{methods} {route.path}")

    assert not missing_models, f"Znaleziono endpointy bez zdefiniowanego 'response_model': {missing_models}"
