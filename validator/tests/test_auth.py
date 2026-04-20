from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import app.security.auth as auth_module
from app.security.auth import (
    auth_callback,
    configure_oauth,
    require_internal_or_user_ui_access,
    login,
    logout,
    require_internal_or_user_api_access,
    require_user_api_access,
    require_user_login,
)


class _AsyncGoogleClient:
    def __init__(self, *, redirect_result=None, token=None):
        self.redirect_calls = []
        self.token_calls = []
        self._redirect_result = redirect_result
        self._token = token or {}

    async def authorize_redirect(self, request, redirect_uri):
        self.redirect_calls.append((request, redirect_uri))
        return self._redirect_result

    async def authorize_access_token(self, request):
        self.token_calls.append(request)
        return self._token


def test_configure_oauth_allows_local_runtime_with_dummy_defaults(monkeypatch):
    register_calls = []
    monkeypatch.setenv("APP_RUNTIME", "local")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("ALLOWED_AUTH_EMAIL", raising=False)
    monkeypatch.setattr(auth_module.oauth, "register", lambda **kwargs: register_calls.append(kwargs))

    configure_oauth(app=object())

    assert len(register_calls) == 1
    assert register_calls[0]["client_id"] == "dummy-client-id"
    assert register_calls[0]["client_secret"] == "dummy-client-secret"


@pytest.mark.parametrize(
    ("env", "expected_message"),
    [
        (
            {
                "APP_RUNTIME": "cloud",
                "GOOGLE_CLIENT_ID": "",
                "GOOGLE_CLIENT_SECRET": "",
                "ALLOWED_AUTH_EMAIL": "admin@example.com",
            },
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are strictly required outside APP_RUNTIME=local.",
        ),
        (
            {
                "APP_RUNTIME": "cloud",
                "GOOGLE_CLIENT_ID": "real-client-id",
                "GOOGLE_CLIENT_SECRET": "real-secret",
                "ALLOWED_AUTH_EMAIL": "dummy-user@example.com",
            },
            "ALLOWED_AUTH_EMAIL is strictly required outside APP_RUNTIME=local to prevent unauthorized access.",
        ),
    ],
)
def test_configure_oauth_fails_fast_in_non_local_runtime(monkeypatch, env, expected_message):
    for key in ("APP_RUNTIME", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "ALLOWED_AUTH_EMAIL"):
        if key in env and env[key]:
            monkeypatch.setenv(key, env[key])
        else:
            monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match=expected_message):
        configure_oauth(app=object())


@pytest.mark.asyncio
async def test_login_returns_html_error_when_google_client_id_is_missing(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "dummy-client-id")

    response = await login(request=SimpleNamespace(url_for=lambda _name: "http://example.com/auth"))

    assert isinstance(response, HTMLResponse)
    assert response.status_code == 500
    assert "OAuth Configuration Missing" in response.body.decode()


@pytest.mark.asyncio
async def test_login_forces_https_for_run_app_callbacks(monkeypatch):
    google = _AsyncGoogleClient(redirect_result={"ok": True})
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "real-client-id")
    monkeypatch.setattr(auth_module, "oauth", SimpleNamespace(google=google))
    request = SimpleNamespace(url_for=lambda _name: "http://demo-service.run.app/auth")

    response = await login(request=request)

    assert response == {"ok": True}
    assert google.redirect_calls[0][1] == "https://demo-service.run.app/auth"


@pytest.mark.asyncio
async def test_auth_callback_denies_unauthorized_email(monkeypatch):
    google = _AsyncGoogleClient(token={"userinfo": {"email": "hacker@example.com"}})
    monkeypatch.setenv("ALLOWED_AUTH_EMAIL", "admin@example.com")
    monkeypatch.setattr(auth_module, "oauth", SimpleNamespace(google=google))
    request = SimpleNamespace(session={"user": {"email": "old@example.com"}})

    response = await auth_callback(request=request)

    assert isinstance(response, HTMLResponse)
    assert response.status_code == 403
    assert "Access Denied" in response.body.decode()
    assert request.session == {"user": {"email": "old@example.com"}}


@pytest.mark.asyncio
async def test_auth_callback_clears_session_and_stores_authorized_user(monkeypatch):
    google = _AsyncGoogleClient(
        token={
            "userinfo": {
                "email": "admin@example.com",
                "name": "Admin User",
            }
        }
    )
    monkeypatch.setenv("ALLOWED_AUTH_EMAIL", "admin@example.com")
    monkeypatch.setattr(auth_module, "oauth", SimpleNamespace(google=google))
    request = SimpleNamespace(session={"stale": "value", "user": {"email": "old@example.com"}})

    response = await auth_callback(request=request)

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/internal/audit"
    assert request.session == {
        "user": {
            "email": "admin@example.com",
            "name": "Admin User",
        }
    }


@pytest.mark.asyncio
async def test_auth_callback_without_userinfo_only_redirects(monkeypatch):
    google = _AsyncGoogleClient(token={})
    monkeypatch.delenv("ALLOWED_AUTH_EMAIL", raising=False)
    monkeypatch.setattr(auth_module, "oauth", SimpleNamespace(google=google))
    request = SimpleNamespace(session={"existing": "session"})

    response = await auth_callback(request=request)

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/internal/audit"
    assert request.session == {"existing": "session"}


@pytest.mark.asyncio
async def test_logout_clears_entire_session():
    request = SimpleNamespace(session={"user": {"email": "admin@example.com"}, "other": "value"})

    response = await logout(request=request)

    assert isinstance(response, RedirectResponse)
    assert response.headers["location"] == "/"
    assert request.session == {}


def test_require_user_login_redirects_when_not_authenticated():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
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
        "client": ("testclient", 50000),
        "session": {},
    }
    request = Request(scope)

    require_user_login(request)
    require_user_api_access(request)


def test_require_internal_or_user_api_access_allows_user_session():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {"user": {"email": "test@example.com"}},
    }
    request = Request(scope)

    require_internal_or_user_api_access(request)


def test_require_internal_or_user_ui_access_allows_user_session():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {"user": {"email": "test@example.com"}},
    }
    request = Request(scope)

    require_internal_or_user_ui_access(request)


def test_require_internal_or_user_ui_access_allows_testclient():
    scope = {
        "type": "http",
        "client": ("testclient", 50000),
        "session": {},
    }
    request = Request(scope)

    require_internal_or_user_ui_access(request)


def test_require_internal_or_user_ui_access_redirects_unauthenticated_external():
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
        "headers": [],
    }
    request = Request(scope)

    with pytest.raises(HTTPException) as exc_info:
        require_internal_or_user_ui_access(request)

    assert exc_info.value.status_code == 307
    assert exc_info.value.headers["Location"] == "/login"


def test_require_internal_or_user_api_access_allows_testclient():
    scope = {
        "type": "http",
        "client": ("testclient", 50000),
        "session": {},
    }
    request = Request(scope)

    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_allows_localhost():
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 12345),
        "session": {},
    }
    request = Request(scope)

    require_internal_or_user_api_access(request)


def test_require_internal_or_user_api_access_allows_internal_secret(monkeypatch):
    monkeypatch.setenv("INTERNAL_SECRET", "super-secret-test-key")
    monkeypatch.setenv("APP_RUNTIME", "local")
    scope = {
        "type": "http",
        "client": ("192.168.1.1", 12345),
        "session": {},
        "headers": [(b"x-internal-secret", b"super-secret-test-key")],
    }
    request = Request(scope)

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

    require_user_login(request)
    require_user_api_access(request)
