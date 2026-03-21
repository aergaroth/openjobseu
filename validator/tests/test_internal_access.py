import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient
from unittest.mock import patch

# Importujemy testowaną zależność (upewnij się, że ścieżka odpowiada Twojej architekturze)
from app.security.internal_access import require_internal_access

# 1. Tworzymy tymczasową instancję aplikacji na potrzeby testów
app = FastAPI()

# Symulujemy żądanie z zewnątrz (TestClient domyślnie używa 'testclient' jako hosta, co omija zabezpieczenia)
@app.middleware("http")
async def override_client_ip(request: Request, call_next):
    request.scope["client"] = ("198.51.100.1", 12345)
    return await call_next(request)

# 2. Zapinamy testowaną zależność na testowy endpoint
@app.post("/internal/test-endpoint", dependencies=[Depends(require_internal_access)])
def dummy_internal_endpoint():
    return {"message": "Success"}

client = TestClient(app)

def test_internal_access_missing_auth_header():
    """Test sprawdza zachowanie endpointu w przypadku braku nagłówka Authorization"""
    response = client.post("/internal/test-endpoint")
    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required for internal endpoints"}

# 3. Patchujemy funkcję weryfikującą token w module, w którym jest ONA WYKORZYSTYWANA
# Zakładamy, że to `app.security.internal_access` importuje i wywołuje `id_token.verify_oauth2_token`
@patch("app.security.internal_access.id_token.verify_oauth2_token")
def test_internal_access_valid_oidc_token(mock_verify, monkeypatch):
    """Test sprawdza poprawnie zweryfikowany token OIDC"""
    monkeypatch.setenv("SCHEDULER_SA_EMAIL", "scheduler-internal@openjobseu.iam.gserviceaccount.com")

    # Symulujemy poprawne działanie biblioteki Google Auth, zwracając payload tokena
    mock_verify.return_value = {
        "email": "scheduler-internal@openjobseu.iam.gserviceaccount.com",
        "aud": "https://dev-openjobseu-123.europe-north1.run.app"
    }
    
    response = client.post(
        "/internal/test-endpoint",
        headers={"Authorization": "Bearer some_valid_token_string"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"message": "Success"}
    mock_verify.assert_called_once()

@patch("app.security.internal_access.id_token.verify_oauth2_token")
def test_internal_access_invalid_oidc_token(mock_verify):
    """Test sprawdza zachowanie w przypadku odrzucenia tokena przez weryfikatora (np. zły audience)"""
    # Symulujemy rzucenie standardowego błędu przez bibliotekę Google Auth
    mock_verify.side_effect = ValueError("Wrong recipient, audience mismatch")
    
    response = client.post(
        "/internal/test-endpoint",
        headers={"Authorization": "Bearer invalid_or_expired_token"}
    )
    
    # Oczekujemy 401 Unauthorized, ponieważ token okazał się nieważny
    assert response.status_code == 401