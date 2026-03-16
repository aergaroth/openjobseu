import pytest
from fastapi import Request, HTTPException
from app.security.auth import (
    require_user_login,
    require_user_api_access,
    require_internal_or_user_api_access,
)


def test_require_user_login_redirects_when_not_authenticated():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),  # Normal external IP
        "session": {},  # No user in session
    }
    request = Request(scope)
    
    with pytest.raises(HTTPException) as exc_info:
        require_user_login(request)
        
    assert exc_info.value.status_code == 307
    assert exc_info.value.headers["Location"] == "/login"


def test_require_user_api_access_returns_401_when_not_authenticated():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
    }
    request = Request(scope)
    
    with pytest.raises(HTTPException) as exc_info:
        require_user_api_access(request)
        
    assert exc_info.value.status_code == 401


def test_dependencies_allow_testclient_without_session():
    scope = {
        "type": "http",
        "client": ("testclient", 50000),  # Pytest TestClient
        "session": {},
    }
    request = Request(scope)
    
    # Should not raise any exceptions
    require_user_login(request)
    require_user_api_access(request)


def test_require_internal_or_user_api_access_allows_user_session():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {"user": {"email": "test@example.com"}},
    }
    request = Request(scope)
    
    # Should not raise
    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_allows_testclient():
    scope = {
        "type": "http",
        "client": ("testclient", 50000),
        "session": {},
    }
    request = Request(scope)
    
    # Should not raise
    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_allows_localhost():
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 12345),
        "session": {},
    }
    request = Request(scope)
    
    # Should not raise
    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_allows_internal_secret(monkeypatch):
    monkeypatch.setenv("INTERNAL_SECRET", "super-secret-test-key")
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
        "headers": [(b"x-internal-secret", b"super-secret-test-key")],
    }
    request = Request(scope)
    
    # Should not raise
    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_blocks_unauthenticated_external():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
        "headers": [],
    }
    request = Request(scope)
    
    with pytest.raises(HTTPException) as exc_info:
        require_internal_or_user_api_access(request)
        
    assert exc_info.value.status_code == 401


def test_dependencies_allow_authenticated_user():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {"user": {"email": "test@example.com"}},
    }
    request = Request(scope)
    
    # Should not raise any exceptions
    require_user_login(request)
    require_user_api_access(request)