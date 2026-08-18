from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .auth import SESSION_COOKIE, bootstrap_configured, get_current_user, setup_required
from .auth_lifecycle import admin_auth_diagnostics, initialize_authentication, public_auth_status
from .config import get_settings
from .database import get_db, get_session_factory, run_migrations
from .models import Session, User


@asynccontextmanager
async def auth_lifespan(_app):
    # This lifespan is merged into the application router. Authentication is fully
    # initialised before requests are accepted and no auth route has to be hit first.
    run_migrations()
    with get_session_factory()() as db:
        initialize_authentication(db)
    yield


router = APIRouter(lifespan=auth_lifespan)
DB = Depends(get_db)


def _public_user(user: User) -> dict[str, object]:
    return {"id": user.id, "username": user.username, "display_name": user.display_name, "is_admin": user.is_admin}


@router.get("/auth/state")
def auth_state(
    response: Response,
    db: DbSession = DB,
    session_token: str | None = SESSION_COOKIE,
):
    public = public_auth_status(db)
    try:
        user = get_current_user(response=response, db=db, session_token=session_token)
        diagnostics = admin_auth_diagnostics(db) if user.is_admin else {}
        return {
            **public,
            "authenticated": True,
            "setup_required": False,
            "user": _public_user(user),
            "admin_bootstrap_configured": bootstrap_configured(),
            "recovery_mode": bool(diagnostics.get("recovery_mode", False)),
            "message": (
                "Administrator recovery mode is still enabled. Disable admin_recovery_mode in Home Assistant Configuration after confirming access."
                if user.is_admin and diagnostics.get("recovery_mode")
                else None
            ),
        }
    except HTTPException:
        message = None
        if public["configuration_error"]:
            message = "Fynvo administrator configuration requires attention. Check the add-on logs and Home Assistant Configuration."
        elif public["setup_required"]:
            message = "Configure the Fynvo administrator in the Home Assistant add-on Configuration page, save and restart the add-on."
        return {
            **public,
            "authenticated": False,
            "user": None,
            "admin_bootstrap_configured": bootstrap_configured(),
            "recovery_mode": False,
            "message": message,
        }


@router.get("/auth/configuration-status")
def public_configuration_status(db: DbSession = DB):
    # Backwards-compatible endpoint retained with intentionally minimal pre-auth data.
    return public_auth_status(db)


@router.get("/auth/diagnostics")
def authentication_diagnostics(
    current_user: User = Depends(get_current_user),
    db: DbSession = DB,
    session_token: str | None = SESSION_COOKIE,
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    diagnostics = admin_auth_diagnostics(db)
    if session_token:
        from .security import hash_token

        session = db.scalar(select(Session).where(Session.token_hash == hash_token(session_token), Session.user_id == current_user.id))
        diagnostics["session_expires_at"] = session.expires_at.isoformat() if session else None
    else:
        diagnostics["session_expires_at"] = None
    return diagnostics
