from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DbSession

from .auth import SESSION_COOKIE, bootstrap_configured, get_current_user, setup_required
from .database import get_db
from .main import public_user
from .schemas import AuthStateResponse

router = APIRouter()
DB = Depends(get_db)


@router.get("/auth/state", response_model=AuthStateResponse)
def auth_state_v12(
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
            admin_bootstrap_configured=True,
            message=None,
        )
    except HTTPException:
        required = setup_required(db)
        configured = bootstrap_configured()
        message = None
        if required and not configured:
            message = "Fynvo requires an administrator account before first use. Configure admin_username, admin_display_name and admin_password in the Home Assistant add-on Configuration page, then restart Fynvo."
        elif required and configured:
            message = "Administrator bootstrap configuration is present but invalid. Check the Home Assistant add-on Configuration page and restart Fynvo."
        return AuthStateResponse(
            authenticated=False,
            setup_required=required,
            user=None,
            admin_bootstrap_configured=configured,
            message=message,
        )
