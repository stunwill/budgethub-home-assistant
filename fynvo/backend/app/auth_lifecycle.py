from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session as DbSession

from .config import Settings, get_settings
from .models import AppConfig, LoginAttempt, Session, User
from .security import hash_password, utcnow

LOGGER = logging.getLogger("fynvo.auth")
MIN_BOOTSTRAP_PASSWORD_LENGTH = 8
CONFIG_FINGERPRINT_KEY = "admin_config_fingerprint"
CONFIG_APPLIED_KEY = "admin_config_applied"
CONFIG_ERROR_KEY = "admin_bootstrap_error"
CONFIG_MIGRATION_KEY = "admin_config_adopted_v013"
AUTH_LAST_STATE_KEY = "auth_last_state"
AUTH_LAST_RESULT_KEY = "auth_last_result"
AUTH_LAST_INIT_KEY = "auth_last_initialised_at"
AUTH_RECOVERY_KEY = "admin_recovery_last_run"
AUTH_BOOTSTRAP_KEY = "admin_bootstrap_completed"


class AuthLifecycleState(StrEnum):
    NO_USERS = "NO_USERS"
    BOOTSTRAP_REQUIRED = "BOOTSTRAP_REQUIRED"
    READY = "READY"
    READY_WITH_CONFIGURATION_WARNING = "READY_WITH_CONFIGURATION_WARNING"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"
    AUTH_CONFIGURATION_ERROR = "AUTH_CONFIGURATION_ERROR"


@dataclass(frozen=True)
class AuthInitResult:
    state: AuthLifecycleState
    action: str
    message: str
    user_id: int | None = None
    username: str | None = None
    sessions_revoked: int = 0
    failed_attempts_cleared: int = 0

    def public(self) -> dict[str, object]:
        return {
            "authentication": "ready" if self.state in {AuthLifecycleState.READY, AuthLifecycleState.READY_WITH_CONFIGURATION_WARNING} else "not_ready",
            "setup_required": self.state in {AuthLifecycleState.NO_USERS, AuthLifecycleState.BOOTSTRAP_REQUIRED},
            "recovery_required": self.state == AuthLifecycleState.RECOVERY_REQUIRED,
            "configuration_error": self.state == AuthLifecycleState.AUTH_CONFIGURATION_ERROR,
        }


def _app_config_value(db: DbSession, key: str) -> str | None:
    row = db.get(AppConfig, key)
    return row.value if row else None


def _set_app_config(db: DbSession, key: str, value: str) -> None:
    db.merge(AppConfig(key=key, value=value, updated_at=utcnow()))


def _credential_fingerprint(username: str, password: str) -> str:
    return sha256(f"{username}\0{password}".encode()).hexdigest()


def validate_admin_values(username: str | None, password: str | None, display_name: str | None) -> tuple[str, str, str]:
    username_value = (username or "").strip().lower()
    display_name_value = (display_name or username_value).strip()
    password_value = password or ""
    if len(username_value) < 3:
        raise ValueError("Administrator username must be at least 3 characters.")
    if not display_name_value:
        raise ValueError("Administrator display name is required.")
    if len(password_value) < MIN_BOOTSTRAP_PASSWORD_LENGTH:
        raise ValueError("Administrator password must be at least 8 characters.")
    if password_value.lower() in {"password", "admin", "changeme", "fynvo", "admin123"}:
        raise ValueError("Administrator password is too easy to guess.")
    return username_value, display_name_value, password_value


def bootstrap_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(settings.admin_username and settings.admin_password)


def _persist_result(db: DbSession, result: AuthInitResult) -> None:
    _set_app_config(db, AUTH_LAST_STATE_KEY, result.state.value)
    _set_app_config(db, AUTH_LAST_RESULT_KEY, result.message)
    _set_app_config(db, AUTH_LAST_INIT_KEY, utcnow().isoformat())
    _set_app_config(db, CONFIG_ERROR_KEY, result.message if result.state in {AuthLifecycleState.AUTH_CONFIGURATION_ERROR, AuthLifecycleState.READY_WITH_CONFIGURATION_WARNING} else "")


def _log_options(settings: Settings) -> None:
    LOGGER.info(
        "Authentication options loaded source=%s username_present=%s password_present=%s recovery_mode=%s session_days=%s configured_username=%s",
        settings.options_source,
        bool(settings.admin_username),
        bool(settings.admin_password),
        settings.admin_recovery_mode,
        settings.session_days,
        (settings.admin_username or "").strip().lower() or "<none>",
    )


def _apply_recovery(db: DbSession, target: User, username: str, display_name: str, password: str) -> tuple[int, int]:
    old_username = target.username
    target.username = username
    target.display_name = display_name
    target.password_hash = hash_password(password)
    target.is_admin = True
    target.is_active = True
    target.updated_at = utcnow()
    db.flush()

    revoked = db.execute(
        update(Session)
        .where(Session.user_id == target.id, Session.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    ).rowcount or 0
    cleared = db.execute(
        delete(LoginAttempt).where(LoginAttempt.username.in_({old_username, username}))
    ).rowcount or 0
    return int(revoked), int(cleared)


def initialize_authentication(db: DbSession, *, settings: Settings | None = None) -> AuthInitResult:
    """Initialise administrator authentication deterministically at application startup.

    This is the single authority for Home Assistant bootstrap/recovery. It never creates a
    second administrator when the recovery target is ambiguous and it updates an existing
    administrator in place so financial ownership foreign keys remain unchanged.
    """

    settings = settings or get_settings()
    _log_options(settings)
    users = list(db.scalars(select(User).order_by(User.id)).all())
    admins = [user for user in users if user.is_admin]
    LOGGER.info("Authentication initialisation started users=%s admins=%s recovery_mode=%s", len(users), len(admins), settings.admin_recovery_mode)

    if not bootstrap_configured(settings):
        state = AuthLifecycleState.NO_USERS if not users else AuthLifecycleState.READY
        result = AuthInitResult(
            state=state,
            action="none",
            message="Administrator bootstrap configuration is not supplied." if not users else "Authentication ready using persisted administrator credentials.",
        )
        with db.begin_nested():
            _persist_result(db, result)
        db.commit()
        LOGGER.warning("Authentication requires administrator bootstrap configuration.") if not users else LOGGER.info("Authentication ready using persisted credentials.")
        return result

    try:
        username, display_name, password = validate_admin_values(settings.admin_username, settings.admin_password, settings.admin_display_name)
    except ValueError as exc:
        result = AuthInitResult(AuthLifecycleState.AUTH_CONFIGURATION_ERROR, "configuration_error", str(exc))
        with db.begin_nested():
            _persist_result(db, result)
        db.commit()
        LOGGER.error("Authentication configuration error: %s", exc)
        return result

    fingerprint = _credential_fingerprint(username, password)
    stored_fingerprint = _app_config_value(db, CONFIG_FINGERPRINT_KEY)

    if not users:
        try:
            with db.begin_nested():
                user = User(username=username, display_name=display_name, password_hash=hash_password(password), is_admin=True, is_active=True)
                db.add(user)
                db.flush()
                _set_app_config(db, AUTH_BOOTSTRAP_KEY, "true")
                _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
                _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
                result = AuthInitResult(AuthLifecycleState.READY, "bootstrap", "Initial administrator created from Home Assistant configuration.", user.id, user.username)
                _persist_result(db, result)
            db.commit()
        except Exception:
            db.rollback()
            LOGGER.exception("Administrator bootstrap failed and was rolled back.")
            raise
        LOGGER.info("Administrator bootstrap completed successfully username=%s", username)
        return result

    configured_user = next((user for user in users if user.username == username), None)

    if settings.admin_recovery_mode:
        target = configured_user
        if target is None and len(admins) == 1:
            target = admins[0]
        if target is None:
            message = "Administrator recovery target is ambiguous. Configure an existing administrator username or reduce the administrator set to one before recovery."
            result = AuthInitResult(AuthLifecycleState.AUTH_CONFIGURATION_ERROR, "recovery_blocked", message)
            with db.begin_nested():
                _persist_result(db, result)
            db.commit()
            LOGGER.error("Administrator recovery blocked: ambiguous target configured_username=%s admin_count=%s", username, len(admins))
            return result

        collision = next((user for user in users if user.username == username and user.id != target.id), None)
        if collision is not None:
            message = "Administrator recovery could not apply because the configured username is already in use."
            result = AuthInitResult(AuthLifecycleState.AUTH_CONFIGURATION_ERROR, "recovery_blocked", message)
            with db.begin_nested():
                _persist_result(db, result)
            db.commit()
            LOGGER.error("Administrator recovery blocked by username collision configured_username=%s", username)
            return result

        try:
            with db.begin_nested():
                revoked, cleared = _apply_recovery(db, target, username, display_name, password)
                _set_app_config(db, AUTH_RECOVERY_KEY, utcnow().isoformat())
                _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
                _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
                _set_app_config(db, CONFIG_MIGRATION_KEY, "true")
                result = AuthInitResult(
                    AuthLifecycleState.READY,
                    "recovery",
                    "Administrator recovery completed successfully. Log in using the configured administrator credentials. Disable admin_recovery_mode after confirming access.",
                    target.id,
                    username,
                    revoked,
                    cleared,
                )
                _persist_result(db, result)
            db.commit()
        except Exception:
            db.rollback()
            LOGGER.exception("Administrator recovery failed and was rolled back username=%s", username)
            raise
        LOGGER.info("Administrator recovery completed successfully username=%s sessions_revoked=%s failed_attempts_cleared=%s", username, revoked, cleared)
        return result

    exact_admin = configured_user if configured_user is not None and configured_user.is_admin else None
    if exact_admin is not None and stored_fingerprint == fingerprint:
        result = AuthInitResult(AuthLifecycleState.READY, "none", "Configured administrator credentials are already applied.", exact_admin.id, exact_admin.username)
        with db.begin_nested():
            _persist_result(db, result)
        db.commit()
        LOGGER.info("Authentication ready configured identity matches persisted administrator username=%s", username)
        return result

    migration_done = _app_config_value(db, CONFIG_MIGRATION_KEY) == "true"
    if len(admins) == 1 and stored_fingerprint is None and not migration_done:
        target = admins[0]
        collision = next((user for user in users if user.username == username and user.id != target.id), None)
        if collision is None:
            try:
                with db.begin_nested():
                    revoked, cleared = _apply_recovery(db, target, username, display_name, password)
                    _set_app_config(db, CONFIG_FINGERPRINT_KEY, fingerprint)
                    _set_app_config(db, CONFIG_APPLIED_KEY, utcnow().isoformat())
                    _set_app_config(db, CONFIG_MIGRATION_KEY, "true")
                    result = AuthInitResult(AuthLifecycleState.READY, "legacy_adoption", "Existing administrator adopted the configured Home Assistant credentials during legacy migration.", target.id, username, revoked, cleared)
                    _persist_result(db, result)
                db.commit()
            except Exception:
                db.rollback()
                LOGGER.exception("Legacy administrator credential adoption failed and was rolled back username=%s", username)
                raise
            LOGGER.info("Legacy administrator credentials adopted username=%s", username)
            return result

    message = "Persisted administrator credentials remain authoritative. Enable admin_recovery_mode for one restart to intentionally apply changed Home Assistant credentials."
    result = AuthInitResult(AuthLifecycleState.READY_WITH_CONFIGURATION_WARNING, "warning", message, admins[0].id if len(admins) == 1 else None, admins[0].username if len(admins) == 1 else None)
    with db.begin_nested():
        _persist_result(db, result)
    db.commit()
    LOGGER.warning("Authentication ready with configuration warning configured_username=%s admin_count=%s", username, len(admins))
    return result


def current_lifecycle_state(db: DbSession) -> AuthLifecycleState:
    raw = _app_config_value(db, AUTH_LAST_STATE_KEY)
    if raw:
        try:
            return AuthLifecycleState(raw)
        except ValueError:
            pass
    users_count = int(db.scalar(select(func.count(User.id))) or 0)
    return AuthLifecycleState.READY if users_count else AuthLifecycleState.NO_USERS


def public_auth_status(db: DbSession) -> dict[str, object]:
    state = current_lifecycle_state(db)
    return {
        "authentication": "ready" if state in {AuthLifecycleState.READY, AuthLifecycleState.READY_WITH_CONFIGURATION_WARNING} else "not_ready",
        "setup_required": state in {AuthLifecycleState.NO_USERS, AuthLifecycleState.BOOTSTRAP_REQUIRED},
        "recovery_required": state == AuthLifecycleState.RECOVERY_REQUIRED,
        "configuration_error": state == AuthLifecycleState.AUTH_CONFIGURATION_ERROR,
    }


def admin_auth_diagnostics(db: DbSession, settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()
    users_count = int(db.scalar(select(func.count(User.id))) or 0)
    admins = list(db.scalars(select(User).where(User.is_admin.is_(True)).order_by(User.id)).all())
    admin = admins[0] if len(admins) == 1 else None
    configured_username = (settings.admin_username or "").strip().lower()
    return {
        "authentication": current_lifecycle_state(db).value,
        "username": admin.username if admin else None,
        "display_name": admin.display_name if admin else None,
        "is_admin": bool(admin and admin.is_admin),
        "is_active": bool(admin and admin.is_active),
        "bootstrap_configured": bootstrap_configured(settings),
        "recovery_mode": settings.admin_recovery_mode,
        "configured_identity_match": bool(admin and configured_username and admin.username == configured_username),
        "last_bootstrap_or_recovery": _app_config_value(db, AUTH_RECOVERY_KEY) or _app_config_value(db, CONFIG_APPLIED_KEY),
        "last_initialised_at": _app_config_value(db, AUTH_LAST_INIT_KEY),
        "last_init_result": _app_config_value(db, AUTH_LAST_RESULT_KEY),
        "user_count": users_count,
        "administrator_count": len(admins),
        "options_source": settings.options_source,
        "session_days": settings.session_days,
    }
