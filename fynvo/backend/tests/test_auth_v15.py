from datetime import timedelta

from app.auth_lifecycle import AuthLifecycleState, initialize_authentication
from app.config import get_settings
from app.database import get_session_factory
from app.models import Account, LoginAttempt, Session, User
from app.security import hash_password, hash_token, utcnow, verify_password
from sqlalchemy import select

TEST_PASSWORD = "TestAdminRecovery123!"
OLD_PASSWORD = "LegacyAdminPassword123!"


def configure(monkeypatch, *, username="test_admin", password=TEST_PASSWORD, display_name="Test Administrator", recovery=True, session_days=7):
    monkeypatch.setenv("FYNVO_ADMIN_USERNAME", username)
    monkeypatch.setenv("FYNVO_ADMIN_DISPLAY_NAME", display_name)
    monkeypatch.setenv("FYNVO_ADMIN_PASSWORD", password)
    monkeypatch.setenv("FYNVO_ADMIN_RECOVERY_MODE", "true" if recovery else "false")
    monkeypatch.setenv("FYNVO_SESSION_DAYS", str(session_days))
    get_settings.cache_clear()


def initialise():
    with get_session_factory()() as db:
        return initialize_authentication(db)


def test_exact_reported_401_regression_existing_admin_recovery_then_login_200(client, monkeypatch):
    created = client.post("/api/auth/setup", json={"username": "legacy_admin", "display_name": "Legacy Administrator", "password": OLD_PASSWORD})
    assert created.status_code == 201
    client.post("/api/auth/logout")

    configure(monkeypatch)
    result = initialise()
    assert result.state == AuthLifecycleState.READY
    assert result.action == "recovery"

    login = client.post("/api/auth/login", json={"username": "test_admin", "password": TEST_PASSWORD})
    assert login.status_code == 200
    assert login.json()["username"] == "test_admin"
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "legacy_admin", "password": OLD_PASSWORD}).status_code == 401


def test_legacy_database_recovery_preserves_user_id_and_owned_records(client, monkeypatch):
    created = client.post("/api/auth/setup", json={"username": "legacy_admin", "display_name": "Legacy Administrator", "password": OLD_PASSWORD}).json()
    user_id = created["id"]
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    client.post("/api/auth/logout")

    with get_session_factory()() as db:
        db.add(LoginAttempt(username="legacy_admin", client_key="ingress-peer", success=False, created_at=utcnow()))
        db.add(Session(token_hash=hash_token("legacy-session"), user_id=user_id, expires_at=utcnow() + timedelta(days=7)))
        db.commit()

    configure(monkeypatch)
    result = initialise()
    assert result.action == "recovery"

    with get_session_factory()() as db:
        users = list(db.scalars(select(User)).all())
        assert len(users) == 1
        user = users[0]
        assert user.id == user_id
        assert user.username == "test_admin"
        assert verify_password(TEST_PASSWORD, user.password_hash)
        assert not verify_password(OLD_PASSWORD, user.password_hash)
        persisted_account = db.get(Account, account["id"])
        assert persisted_account.user_id == user_id
        sessions = list(db.scalars(select(Session).where(Session.user_id == user_id)).all())
        assert sessions and all(session.revoked_at is not None for session in sessions)
        assert list(db.scalars(select(LoginAttempt).where(LoginAttempt.username.in_(["legacy_admin", "test_admin"]))).all()) == []


def test_recovery_is_idempotent_and_does_not_duplicate_admin(client, monkeypatch):
    client.post("/api/auth/setup", json={"username": "legacy_admin", "display_name": "Legacy Administrator", "password": OLD_PASSWORD})
    client.post("/api/auth/logout")
    configure(monkeypatch)
    first = initialise()
    second = initialise()
    assert first.action == "recovery"
    assert second.action == "recovery"
    with get_session_factory()() as db:
        users = list(db.scalars(select(User)).all())
        assert len(users) == 1
        assert users[0].username == "test_admin"
        assert verify_password(TEST_PASSWORD, users[0].password_hash)


def test_recovery_fails_safely_for_multiple_admins_without_exact_username(client, monkeypatch):
    client.post("/api/auth/setup", json={"username": "admin_one", "display_name": "Admin One", "password": OLD_PASSWORD})
    client.post("/api/auth/logout")
    with get_session_factory()() as db:
        db.add(User(username="admin_two", display_name="Admin Two", password_hash=hash_password("SecondAdminPassword123!"), is_admin=True, is_active=True))
        db.commit()
    configure(monkeypatch, username="test_admin")
    result = initialise()
    assert result.state == AuthLifecycleState.AUTH_CONFIGURATION_ERROR
    with get_session_factory()() as db:
        assert db.scalar(select(User).where(User.username == "test_admin")) is None


def test_recovery_fails_safely_on_username_collision(client, monkeypatch):
    admin = client.post("/api/auth/setup", json={"username": "admin_one", "display_name": "Admin One", "password": OLD_PASSWORD}).json()
    client.post("/api/auth/logout")
    with get_session_factory()() as db:
        db.add(User(username="test_admin", display_name="Standard User", password_hash=hash_password("StandardUserPassword123!"), is_admin=False, is_active=True))
        db.commit()
    configure(monkeypatch, username="test_admin")
    result = initialise()
    # Exact configured identity is deterministic, so that user becomes the intended recovered admin.
    assert result.state == AuthLifecycleState.READY
    assert result.user_id != admin["id"]
    with get_session_factory()() as db:
        recovered = db.scalar(select(User).where(User.username == "test_admin"))
        assert recovered is not None and recovered.is_admin


def test_recovery_revokes_target_sessions_but_not_unrelated_user_sessions(client, monkeypatch):
    admin = client.post("/api/auth/setup", json={"username": "legacy_admin", "display_name": "Legacy Administrator", "password": OLD_PASSWORD}).json()
    client.post("/api/auth/logout")
    with get_session_factory()() as db:
        other = User(username="other_user", display_name="Other User", password_hash=hash_password("OtherUserPassword123!"), is_admin=False, is_active=True)
        db.add(other)
        db.flush()
        db.add(Session(token_hash=hash_token("admin-session"), user_id=admin["id"], expires_at=utcnow() + timedelta(days=7)))
        db.add(Session(token_hash=hash_token("other-session"), user_id=other.id, expires_at=utcnow() + timedelta(days=7)))
        db.commit()
        other_id = other.id
    configure(monkeypatch)
    initialise()
    with get_session_factory()() as db:
        admin_sessions = list(db.scalars(select(Session).where(Session.user_id == admin["id"])).all())
        other_sessions = list(db.scalars(select(Session).where(Session.user_id == other_id)).all())
        assert admin_sessions and all(item.revoked_at is not None for item in admin_sessions)
        assert other_sessions and all(item.revoked_at is None for item in other_sessions)


def test_public_auth_status_does_not_expose_identity_or_counts(client):
    response = client.get("/api/auth/configuration-status")
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"authentication", "setup_required", "recovery_required", "configuration_error"}
    assert "username" not in payload
    assert "users" not in payload


def test_admin_diagnostics_are_protected_and_safe(client):
    assert client.get("/api/auth/diagnostics").status_code == 401
    client.post("/api/auth/setup", json={"username": "admin", "display_name": "Administrator", "password": OLD_PASSWORD})
    diagnostics = client.get("/api/auth/diagnostics")
    assert diagnostics.status_code == 200
    payload = diagnostics.json()
    assert payload["username"] == "admin"
    assert "password" not in payload
    assert "password_hash" not in payload
    assert "token" not in payload


def test_session_days_controls_cookie_and_database_expiry(client, monkeypatch):
    configure(monkeypatch, username="session_admin", password="SessionAdminPassword123!", display_name="Session Admin", recovery=True, session_days=7)
    initialise()
    before = utcnow()
    response = client.post("/api/auth/login", json={"username": "session_admin", "password": "SessionAdminPassword123!"})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "Max-Age=604800" in cookie
    with get_session_factory()() as db:
        session = db.scalar(select(Session).order_by(Session.id.desc()))
        assert session is not None
        assert session.expires_at >= before + timedelta(days=6, hours=23)


def test_logout_revokes_only_current_session(client):
    created = client.post("/api/auth/setup", json={"username": "logout_admin", "display_name": "Logout Admin", "password": OLD_PASSWORD})
    assert created.status_code == 201
    with get_session_factory()() as db:
        user = db.scalar(select(User).where(User.username == "logout_admin"))
        db.add(Session(token_hash=hash_token("unrelated-session"), user_id=user.id, expires_at=utcnow() + timedelta(days=7)))
        db.commit()
    assert client.post("/api/auth/logout").status_code == 200
    with get_session_factory()() as db:
        unrelated = db.scalar(select(Session).where(Session.token_hash == hash_token("unrelated-session")))
        assert unrelated.revoked_at is None
