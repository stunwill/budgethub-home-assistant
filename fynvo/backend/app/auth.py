from datetime import timedelta
from hashlib import sha256

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
CONFIG_FINGERPRINT_KEY = "admin_config_fingerprint"
CONFIG_APPLIED_KEY = "admin_config_applied"
CONFIG_ERROR_KEY = "admin_bootstrap_error"
CONFIG_MIGRATION_KEY = "admin_config_adopted_v013"


def get_client_key(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def bootstrap_configured() -> bool:
    settings = get_settings()
    return bool(settings.admin_username and settings.admin_password)


def _app_config_value(db: DbSession, key: str) -> str | None:
    row = db.get(AppConfig, key)
    return row.value if row else None


def _set_app_config(db: DbSession, key: str, value: str) -> None:
    db.merge(AppConfig(key=key, value=value, updated_at=utcnow()))


def _credential_fingerprint(username: str, password: str) -> str:
    return sha256(f"{username}\0{password}".encode()).hexdigest()


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


def _apply_credentials(user: User, username: str, display_name: str, password: str) -> None:
    user.username = username
    user.display_name = display_name
    user.password_hash = hash_password(password)
    user.is_admin = True
    user.is_active = True
    user.updated_at = utcnow()


def bootstrap_initial_admin(db: DbSession) -> dict[str, str | bool]:
    """Apply the supported Home Assistant administrator bootstrap/recovery configuration.

    v0.12 only applied configured credentials when the database contained no users. Existing
    installations could therefore show one username/password in Home Assistant while a different
    persisted account remained authoritative. v0.13 adopts configured credentials once for a
    single legacy administrator, then requires explicit recovery mode for later credential resets.
    """

    settings = get_settings()
    users = list(db.scalars(select(User).order_by(User.id)).all())
    if not bootstrap_configured():
        return {"created": False, "recovered": False, "adopted": False, "message": "No administrator bootstrap configuration supplied."}

    try:
        username, display_name, password = _validate_admin_values(
            settings.admin_username,
            settings.admin_password,
            settings.admin_display_name,
        )
    except ValueError as exc:
        _set_app_config(db, CONFIG_ERROR_KEY, str(exc))
        db.commit()
        return {"created": False, "recovered": False, "adopted": False, "message": str(exc)}

    fingerprint = _credential_fingerprint(username, password)
    stored_fingerprint = _app_config_value(db, CONFIG_FINGERPRINT_KEY)

    if not users:
        user = User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
        _set_app_config(db, "admin_bootstrap_completed", "true")
        _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
        _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
        _set_app_config(db, CONFIG_ERROR_KEY, "")
        db.commit()
        return {"created": True, "recovered": False, "adopted": False, "message": "Initial administrator created from Home Assistant configuration."}

    admins = [user for user in users if user.is_admin]
    configured_user = next((user for user in users if user.username == username), None)

    if settings.admin_recovery_mode:
        target = configured_user
        if target is None and len(admins) == 1:
            target = admins[0]
        if target is None:
            target = User(username=username, display_name=display_name, password_hash=hash_password(password), is_admin=True, is_active=True)
            db.add(target)
        else:
            collision = db.scalar(select(User).where(User.username == username, User.id != target.id))
            if collision is not None:
                message = "Administrator recovery could not apply because the configured username is already in use."
                _set_app_config(db, CONFIG_ERROR_KEY, message)
                db.commit()
                return {"created": False, "recovered": False, "adopted": False, "message": message}
            _apply_credentials(target, username, display_name, password)
        _set_app_config(db, "admin_recovery_last_run", utcnow().isoformat())
        _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
        _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
        _set_app_config(db, CONFIG_ERROR_KEY, "")
        db.commit()
        return {"created": False, "recovered": True, "adopted": False, "message": "Administrator credential recovery applied. Turn recovery mode off after confirming login."}

    # v0.13 migration for the reported v0.12 failure: if one legacy administrator exists and the
    # HA configuration has never been applied, adopt it once. This preserves the user row and all
    # financial ownership references instead of deleting/recreating the account.
    migration_done = _app_config_value(db, CONFIG_MIGRATION_KEY) == "true"
    if len(admins) == 1 and stored_fingerprint is None and not migration_done:
        target = admins[0]
        collision = db.scalar(select(User).where(User.username == username, User.id != target.id))
        if collision is None:
            _apply_credentials(target, username, display_name, password)
            _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
            _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
            _set_app_config(db, CONFIG_MIGRATION_KEY, "true")
            _set_app_config(db, CONFIG_ERROR_KEY, "")
            db.commit()
            return {"created": False, "recovered": False, "adopted": True, "message": "Existing administrator adopted the configured Home Assistant credentials for v0.13.0."}

    if stored_fingerprint == fingerprint:
        _set_app_config(db, CONFIG_ERROR_KEY, "")
        db.commit()
        return {"created": False, "recovered": False, "adopted": False, "message": "Configured administrator credentials are already applied."}

    message = "Administrator already exists. To intentionally apply changed Home Assistant credentials, enable admin_recovery_mode for one restart, then turn it off."
    _set_app_config(db, CONFIG_ERROR_KEY, message)
    db.commit()
    return {"created": False, "recovered": False, "adopted": False, "message": message}


def setup_required(db: DbSession) -> bool:
    # Always evaluate configured bootstrap/recovery state. v0.12 only called bootstrap when there
    # were zero users, which meant changed configuration could never repair an existing account.
    if bootstrap_configured():
        bootstrap_initial_admin(db)
    return (db.scalar(select(func.count(User.id))) or 0) == 0


def authentication_status(db: DbSession) -> dict[str, str | int | bool | None]:
    users_count = db.scalar(select(func.count(User.id))) or 0
    admin = db.scalar(select(User).where(User.is_admin.is_(True)).order_by(User.id))
    return {
        "ready": users_count > 0,
        "administrator_configured": admin is not None,
        "administrator_username": admin.username if admin else None,
        "users": int(users_count),
        "bootstrap_configured": bootstrap_configured(),
        "configuration_message": _app_config_value(db, CONFIG_ERROR_KEY) or None,
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
