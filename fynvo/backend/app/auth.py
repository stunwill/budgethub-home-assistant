from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session as DbSession

from .auth_lifecycle import (
    admin_auth_diagnostics,
    bootstrap_configured,
    initialize_authentication,
    public_auth_status,
    validate_admin_values,
)
from .config import get_settings
from .database import get_db
from .models import LoginAttempt, Session, User
from .security import (
    expiry_from_now,
    hash_password,
    hash_token,
    new_session_token,
    utcnow,
    verify_password,
)

DB_DEPENDENCY = Depends(get_db)
SESSION_COOKIE = Cookie(default=None, alias="fynvo_session")


def get_client_key(request: Request) -> str:
    """Return a conservative deployment key for rate limiting.

    Home Assistant ingress commonly proxies many browser requests through one peer. We do not
    trust forwarding headers supplied by arbitrary clients. Rate limiting is primarily scoped by
    normalised account identity, with the direct peer only as a secondary dimension.
    """

    return request.client.host if request.client else "unknown"


def bootstrap_initial_admin(db: DbSession) -> dict[str, str | bool | int | None]:
    """Compatibility wrapper for the authoritative v0.15 startup lifecycle service."""

    result = initialize_authentication(db)
    return {
        "created": result.action == "bootstrap",
        "recovered": result.action == "recovery",
        "adopted": result.action == "legacy_adoption",
        "message": result.message,
        "state": result.state.value,
        "user_id": result.user_id,
    }


def setup_required(db: DbSession) -> bool:
    return (db.scalar(select(func.count(User.id))) or 0) == 0


def authentication_status(db: DbSession) -> dict[str, object]:
    public = public_auth_status(db)
    return {
        "ready": public["authentication"] == "ready",
        "administrator_configured": not bool(public["setup_required"]),
        "bootstrap_configured": bootstrap_configured(),
        "configuration_error": public["configuration_error"],
        "recovery_required": public["recovery_required"],
    }


def is_rate_limited(db: DbSession, username: str, client_key: str) -> bool:
    settings = get_settings()
    window_start = utcnow() - timedelta(seconds=settings.login_attempt_window_seconds)
    count = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.username == username,
            LoginAttempt.client_key == client_key,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= window_start,
        )
    )
    return bool(count and count >= settings.max_login_attempts)


def record_login_attempt(db: DbSession, username: str, client_key: str, success: bool) -> None:
    if success:
        db.execute(
            delete(LoginAttempt).where(
                LoginAttempt.username == username,
                LoginAttempt.client_key == client_key,
                LoginAttempt.success.is_(False),
            )
        )
    db.add(LoginAttempt(username=username, client_key=client_key, success=success))
    db.commit()


def create_initial_admin(db: DbSession, username: str, password: str, display_name: str) -> User:
    if not setup_required(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Initial setup has already been completed")
    try:
        username_value, display_name_value, password_value = validate_admin_values(username, password, display_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user = User(username=username_value, display_name=display_name_value, password_hash=hash_password(password_value), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: DbSession, username: str, password: str, client_key: str) -> User:
    username_normalised = username.strip().lower()
    status_info = public_auth_status(db)
    if status_info["configuration_error"]:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication configuration requires administrator attention")
    if status_info["recovery_required"]:
        raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="Administrator recovery is required")
    if setup_required(db):
        raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="Administrator account is not configured")
    if is_rate_limited(db, username_normalised, client_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed login attempts. Try again later.")
    disabled_user = db.scalar(select(User).where(User.username == username_normalised, User.is_active.is_(False)))
    if disabled_user is not None:
        record_login_attempt(db, username_normalised, client_key, success=False)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    user = db.scalar(select(User).where(User.username == username_normalised, User.is_active.is_(True)))
    if user is None or not verify_password(password, user.password_hash):
        record_login_attempt(db, username_normalised, client_key, success=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    record_login_attempt(db, username_normalised, client_key, success=True)
    return user


def start_session(response: Response, db: DbSession, user: User) -> str:
    settings = get_settings()
    token = new_session_token()
    db.add(Session(token_hash=hash_token(token), user_id=user.id, expires_at=expiry_from_now(settings.session_expiry_minutes)))
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_expiry_minutes * 60,
        path="/",
    )
    return token


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.session_cookie_name, path="/", secure=settings.cookie_secure, httponly=True, samesite="lax")


def get_current_user(
    response: Response,
    db: DbSession = DB_DEPENDENCY,
    session_token: str | None = SESSION_COOKIE,
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    session = db.scalar(select(Session).where(Session.token_hash == hash_token(session_token)))
    if session is None or session.revoked_at is not None or session.expires_at <= utcnow():
        clear_session_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = db.scalar(select(User).where(User.id == session.user_id, User.is_active.is_(True)))
    if user is None:
        clear_session_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def revoke_current_session(response: Response, db: DbSession, token: str | None) -> None:
    if token:
        session = db.scalar(select(Session).where(Session.token_hash == hash_token(token)))
        if session:
            session.revoked_at = utcnow()
            db.commit()
    clear_session_cookie(response)


def revoke_user_sessions(db: DbSession, user_id: int) -> int:
    sessions = list(db.scalars(select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))).all())
    now = utcnow()
    for session in sessions:
        session.revoked_at = now
    db.commit()
    return len(sessions)


__all__ = [
    "SESSION_COOKIE",
    "admin_auth_diagnostics",
    "authenticate_user",
    "authentication_status",
    "bootstrap_configured",
    "bootstrap_initial_admin",
    "clear_session_cookie",
    "create_initial_admin",
    "get_client_key",
    "get_current_user",
    "revoke_current_session",
    "revoke_user_sessions",
    "setup_required",
    "start_session",
]
