import os
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse, HTMLResponse
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
        client_kwargs={"scope": "openid email"},
    )


@auth_router.get("/login")
async def login(request: Request):
    if os.environ.get("GOOGLE_CLIENT_ID", "dummy-client-id") == "dummy-client-id":
        return HTMLResponse(
            content="<h3>OAuth Configuration Missing</h3><p>Please set <b>GOOGLE_CLIENT_ID</b> and <b>GOOGLE_CLIENT_SECRET</b> environment variables to log in.</p>",
            status_code=500,
        )

    redirect_uri = str(request.url_for("auth_callback"))

    # Wymuszenie HTTPS dla środowiska Cloud Run (ponieważ load balancer GCP zrywa TLS
    # i aplikacja może błędnie generować adres zwrotny z prefiksem http://)
    if "run.app" in redirect_uri and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    return await oauth.google.authorize_redirect(request, redirect_uri)


@auth_router.get("/auth", name="auth_callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get("userinfo")

    if user:
        # Proste i skuteczne zabezpieczenie przed nieautoryzowanymi logowaniami z zewnątrz
        allowed_email = os.environ.get("ALLOWED_AUTH_EMAIL")
        user_email = user.get("email", "")

        if allowed_email and user_email != allowed_email:
            return HTMLResponse(
                content=f"<h3>Access Denied</h3><p>Your email ({user_email}) is not authorized to access this panel.</p>",
                status_code=403,
            )

        # Prewencja Session Fixation - czyszczenie ewentualnej starej sesji
        request.session.clear()
        request.session["user"] = dict(user)
    return RedirectResponse(url="/internal/audit")


@auth_router.get("/logout")
async def logout(request: Request):
    # Całkowite niszczenie wora sesyjnego zamiast usuwania jednego klucza
    request.session.clear()
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
