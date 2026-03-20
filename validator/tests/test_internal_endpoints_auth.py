import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from app.security.auth import (
    require_user_login,
    require_user_api_access,
    require_internal_or_user_api_access,
)

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
                require_internal_or_user_api_access
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