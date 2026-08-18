from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DbSession

from .auth import (
    SESSION_COOKIE,
    authentication_status,
    bootstrap_configured,
    get_current_user,
    setup_required,
)
from .database import get_db
from .models import User
from .schemas import AuthStateResponse, UserResponse

router = APIRouter()
DB = Depends(get_db)


def public_user(user: User) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name, is_admin=user.is_admin)


@router.get("/auth/state", response_model=AuthStateResponse)
def auth_state_v13(
    response: Response,
    db: DbSession = DB,
    session_token: str | None = SESSION_COOKIE,
):
    try:
        user = get_current_user(response=response, db=db, session_token=session_token)
        return AuthStateResponse(
            authenticated=True,
            setup_required=False,
            user=public_user(user),
            admin_bootstrap_configured=bootstrap_configured(),
            message=None,
        )
    except HTTPException:
        required = setup_required(db)
        status_info = authentication_status(db)
        message = status_info.get("configuration_message")
        if required and not status_info["bootstrap_configured"]:
            message = (
                "Fynvo requires an administrator account before first use. Configure the "
                "administrator in the Home Assistant add-on Configuration page, or create the "
                "administrator here."
            )
        elif required and status_info["bootstrap_configured"] and not message:
            message = "Administrator bootstrap configuration is present but could not be applied."
        return AuthStateResponse(
            authenticated=False,
            setup_required=required,
            user=None,
            admin_bootstrap_configured=bool(status_info["bootstrap_configured"]),
            message=message,
        )


@router.get("/auth/configuration-status")
def auth_configuration_status(db: DbSession = DB):
    status_info = authentication_status(db)
    return {
        "authentication": "ready" if status_info["ready"] else "setup_required",
        "administrator": "configured" if status_info["administrator_configured"] else "not_configured",
        "administrator_username": status_info["administrator_username"],
        "users": status_info["users"],
        "home_assistant_bootstrap_configured": status_info["bootstrap_configured"],
        "configuration_message": status_info["configuration_message"],
    }
