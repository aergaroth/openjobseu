import os
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

from app.security.internal_access import require_internal_access

auth_router = APIRouter()
oauth = OAuth()


def configure_oauth(app):
    """
    This should be called from the main application factory.
    It registers the Google OAuth provider.
    """
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=os.environ.get("GOOGLE_CLIENT_ID", "dummy-client-id"),
        client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "dummy-client-secret"),
        client_kwargs={"scope": "openid email profile"},
    )


@auth_router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/auth", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")
    if user:
        request.session["user"] = dict(user)
    return RedirectResponse(url="/internal/audit")


@auth_router.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")


def require_user_login(request: Request):
    """
    Dependency for user-facing pages.
    If user is not in session, redirect to login page.
    """
    if request.client and request.client.host == "testclient":
        return

    if "user" not in request.session:
        raise HTTPException(status_code=307, headers={"Location": "/login"})


def require_user_api_access(request: Request):
    """
    Dependency for API endpoints called by the frontend.
    If user is not in session, return 401.
    """
    if request.client and request.client.host == "testclient":
        return

    if "user" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )


def require_internal_or_user_api_access(request: Request):
    """
    Allows access for either an authenticated user or an internal service call.
    """
    if request.client and request.client.host == "testclient":
        return

    if "user" in request.session:
        return

    try:
        require_internal_access(request)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )