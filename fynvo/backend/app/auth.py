from datetime import timedelta

from fastapi import Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from .config import get_settings
from .database import get_db
from .models import AppConfig, LoginAttempt, Session, User
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
MIN_BOOTSTRAP_PASSWORD_LENGTH = 8


def get_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def bootstrap_configured() -> bool:
    settings = get_settings()
    return bool(settings.admin_username and settings.admin_password)


def setup_required(db: DbSession) -> bool:
    if db.scalar(select(func.count(User.id))) == 0 and bootstrap_configured():
        bootstrap_initial_admin(db)
    return db.scalar(select(func.count(User.id))) == 0


def _validate_admin_values(username: str | None, password: str | None, display_name: str | None) -> tuple[str, str, str]:
    username_value = (username or "").strip().lower()
    display_name_value = (display_name or username_value).strip()
    password_value = password or ""
    if len(username_value) < 3:
        raise ValueError("Administrator username must be at least 3 characters.")
    if len(display_name_value) < 1:
        raise ValueError("Administrator display name is required.")
    if len(password_value) < MIN_BOOTSTRAP_PASSWORD_LENGTH:
        raise ValueError("Administrator password must be at least 8 characters.")
    if password_value.lower() in {"password", "admin", "changeme", "fynvo", "admin123"}:
        raise ValueError("Administrator password is too easy to guess.")
    return username_value, display_name_value, password_value


def bootstrap_initial_admin(db: DbSession) -> dict[str, str | bool]:
    settings = get_settings()
    users_count = db.scalar(select(func.count(User.id))) or 0
    if users_count == 0:
        if not bootstrap_configured():
            return {"created": False, "recovered": False, "message": "No administrator bootstrap configuration supplied."}
        try:
            username, display_name, password = _validate_admin_values(settings.admin_username, settings.admin_password, settings.admin_display_name)
        except ValueError as exc:
            db.merge(AppConfig(key="admin_bootstrap_error", value=str(exc), updated_at=utcnow()))
            db.commit()
            return {"created": False, "recovered": False, "message": str(exc)}
        user = User(username=username, display_name=display_name, password_hash=hash_password(password), is_admin=True, is_active=True)
        db.add(user)
        db.merge(AppConfig(key="admin_bootstrap_completed", value="true", updated_at=utcnow()))
        db.merge(AppConfig(key="admin_bootstrap_error", value="", updated_at=utcnow()))
        db.commit()
        return {"created": True, "recovered": False, "message": "Initial administrator created from Home Assistant configuration."}
    if settings.admin_recovery_mode:
        try:
            username, display_name, password = _validate_admin_values(settings.admin_username, settings.admin_password, settings.admin_display_name)
        except ValueError as exc:
            db.merge(AppConfig(key="admin_bootstrap_error", value=str(exc), updated_at=utcnow()))
            db.commit()
            return {"created": False, "recovered": False, "message": str(exc)}
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(username=username, display_name=display_name, password_hash=hash_password(password), is_admin=True, is_active=True)
            db.add(user)
        else:
            user.display_name = display_name
            user.password_hash = hash_password(password)
            user.is_admin = True
            user.is_active = True
            user.updated_at = utcnow()
        db.merge(AppConfig(key="admin_recovery_last_run", value=utcnow().isoformat(), updated_at=utcnow()))
        db.commit()
        return {"created": False, "recovered": True, "message": "Administrator recovery mode reset the configured account. Turn recovery mode off after login."}
    return {"created": False, "recovered": False, "message": "Administrator already exists. Bootstrap configuration was ignored."}


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
    db.add(LoginAttempt(username=username, client_key=client_key, success=success))
    db.commit()


def create_initial_admin(db: DbSession, username: str, password: str, display_name: str) -> User:
    if not setup_required(db):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Initial setup has already been completed")
    try:
        username_value, display_name_value, password_value = _validate_admin_values(username, password, display_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    user = User(username=username_value, display_name=display_name_value, password_hash=hash_password(password_value), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: DbSession, username: str, password: str, client_key: str) -> User:
    username_normalised = username.strip().lower()
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
    response.delete_cookie(key=settings.session_cookie_name, path="/")


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
