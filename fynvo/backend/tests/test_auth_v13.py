from sqlalchemy import select

from app.config import get_settings
from app.database import get_session_factory
from app.models import AppConfig, User
from app.security import verify_password


def _configure_admin(monkeypatch, username="stu", password="ConfiguredPassword123!", display_name="Stu", recovery=False):
    monkeypatch.setenv("FYNVO_ADMIN_USERNAME", username)
    monkeypatch.setenv("FYNVO_ADMIN_DISPLAY_NAME", display_name)
    monkeypatch.setenv("FYNVO_ADMIN_PASSWORD", password)
    monkeypatch.setenv("FYNVO_ADMIN_RECOVERY_MODE", "true" if recovery else "false")
    get_settings.cache_clear()


def test_configured_credentials_adopt_single_legacy_administrator(client, monkeypatch):
    client.post("/api/auth/setup", json={"username": "legacy", "display_name": "Legacy", "password": "LegacyPassword123!"})
    client.post("/api/auth/logout")

    _configure_admin(monkeypatch)
    state = client.get("/api/auth/state")
    assert state.status_code == 200
    assert state.json()["setup_required"] is False

    assert client.post("/api/auth/login", json={"username": "legacy", "password": "LegacyPassword123!"}).status_code == 401
    login = client.post("/api/auth/login", json={"username": "stu", "password": "ConfiguredPassword123!"})
    assert login.status_code == 200
    assert login.json()["display_name"] == "Stu"

    with get_session_factory()() as db:
        users = list(db.scalars(select(User)).all())
        assert len(users) == 1
        assert users[0].username == "stu"
        assert "ConfiguredPassword123!" not in users[0].password_hash
        assert verify_password("ConfiguredPassword123!", users[0].password_hash)
        assert db.get(AppConfig, "admin_config_adopted_v013").value == "true"


def test_config_change_after_adoption_requires_explicit_recovery(client, monkeypatch):
    _configure_admin(monkeypatch, username="stu", password="InitialPassword123!")
    assert client.get("/api/auth/state").json()["setup_required"] is False
    assert client.post("/api/auth/login", json={"username": "stu", "password": "InitialPassword123!"}).status_code == 200
    client.post("/api/auth/logout")

    _configure_admin(monkeypatch, username="stu", password="ReplacementPassword123!", recovery=False)
    assert client.post("/api/auth/login", json={"username": "stu", "password": "ReplacementPassword123!"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "stu", "password": "InitialPassword123!"}).status_code == 200

    client.post("/api/auth/logout")
    _configure_admin(monkeypatch, username="stu", password="ReplacementPassword123!", recovery=True)
    assert client.post("/api/auth/login", json={"username": "stu", "password": "ReplacementPassword123!"}).status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "stu", "password": "InitialPassword123!"}).status_code == 401


def test_recovery_does_not_duplicate_existing_administrator(client, monkeypatch):
    _configure_admin(monkeypatch, username="owner", password="OwnerPassword123!")
    assert client.get("/api/auth/state").json()["setup_required"] is False
    client.post("/api/auth/logout")

    _configure_admin(monkeypatch, username="owner", password="RecoveredPassword123!", recovery=True)
    assert client.post("/api/auth/login", json={"username": "owner", "password": "RecoveredPassword123!"}).status_code == 200

    with get_session_factory()() as db:
        assert len(list(db.scalars(select(User)).all())) == 1
