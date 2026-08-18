from app.auth_lifecycle import initialize_authentication
from app.config import get_settings
from app.database import get_session_factory
from app.security import hash_password, verify_password


def _run_auth_startup():
    with get_session_factory()() as db:
        return initialize_authentication(db)


def test_health_endpoint_reports_v0170(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["service"] == "Fynvo"
    assert response.json()["version"] == "0.17.0"


def test_password_hashing_does_not_store_plaintext():
    stored = hash_password("CorrectHorseBatteryStaple")
    assert "CorrectHorseBatteryStaple" not in stored
    assert verify_password("CorrectHorseBatteryStaple", stored)
    assert not verify_password("wrong", stored)


def test_setup_login_protected_dashboard_logout_flow(client):
    state = client.get("/api/auth/state")
    assert state.json()["setup_required"] is True

    setup = client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "ChangeMe123!"})
    assert setup.status_code == 201
    assert setup.json()["username"] == "stu"
    assert "password_hash" not in setup.text

    dashboard = client.get("/api/dashboard/overview")
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"]["currency"] == "AUD"
    assert "incomplete_recurring_count" in dashboard.json()["summary"]
    assert "planned_item_count" in dashboard.json()["summary"]

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200

    rejected = client.get("/api/dashboard/overview")
    assert rejected.status_code == 401

    login = client.post("/api/auth/login", json={"username": "stu", "password": "ChangeMe123!"})
    assert login.status_code == 200
    assert client.get("/api/auth/me").json()["display_name"] == "Stu"


def test_failed_login_is_rejected(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "ChangeMe123!"})
    client.post("/api/auth/logout")
    response = client.post("/api/auth/login", json={"username": "stu", "password": "wrong"})
    assert response.status_code == 401


def test_password_change(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "ChangeMe123!"})
    response = client.post("/api/auth/change-password", json={"current_password": "ChangeMe123!", "new_password": "NewPassword123!"})
    assert response.status_code == 200
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"username": "stu", "password": "ChangeMe123!"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "stu", "password": "NewPassword123!"}).status_code == 200


def test_admin_bootstrap_from_home_assistant_configuration(client, monkeypatch):
    monkeypatch.setenv("FYNVO_ADMIN_USERNAME", "owner")
    monkeypatch.setenv("FYNVO_ADMIN_DISPLAY_NAME", "Owner")
    monkeypatch.setenv("FYNVO_ADMIN_PASSWORD", "OwnerPassword123!")
    get_settings.cache_clear()
    result = _run_auth_startup()
    assert result.action == "bootstrap"

    state = client.get("/api/auth/state").json()
    assert state["setup_required"] is False
    login = client.post("/api/auth/login", json={"username": "owner", "password": "OwnerPassword123!"})
    assert login.status_code == 200
    assert login.json()["is_admin"] is True
    assert "OwnerPassword123!" not in login.text

    client.post("/api/auth/logout")
    state_again = client.get("/api/auth/state").json()
    assert state_again["setup_required"] is False
    assert client.post("/api/auth/login", json={"username": "owner", "password": "OwnerPassword123!"}).status_code == 200


def test_invalid_admin_bootstrap_does_not_create_user(client, monkeypatch):
    monkeypatch.setenv("FYNVO_ADMIN_USERNAME", "ow")
    monkeypatch.setenv("FYNVO_ADMIN_PASSWORD", "password")
    get_settings.cache_clear()
    result = _run_auth_startup()
    assert result.state.value == "AUTH_CONFIGURATION_ERROR"
    state = client.get("/api/auth/state").json()
    assert state["configuration_error"] is True
    assert client.post("/api/auth/login", json={"username": "ow", "password": "password"}).status_code == 503
