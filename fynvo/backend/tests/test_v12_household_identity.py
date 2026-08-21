from app.database import get_engine
from sqlalchemy import text


def _setup_admin(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201
    return response.json()


def _create_member(client, username="kristy", role="household_member"):
    response = client.post(
        "/api/household/members",
        json={
            "username": username,
            "display_name": username.title(),
            "role": role,
            "temporary_password": "Temporary123!",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_setup_admin_gets_initial_household_membership_and_schema_13(client):
    _setup_admin(client)
    household = client.get("/api/household/current")
    assert household.status_code == 200
    payload = household.json()
    assert payload["role"] == "administrator"
    assert payload["member_count"] == 1
    assert payload["currency"] == "AUD"

    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar() == 13
        membership = connection.execute(text("""
            SELECT hm.role, hm.status, u.username
            FROM household_memberships hm JOIN users u ON u.id=hm.user_id
        """)).mappings().one()
        assert membership["role"] == "administrator"
        assert membership["status"] == "active"
        assert membership["username"] == "stu"


def test_admin_can_create_and_manage_household_members_without_exposing_secrets(client):
    _setup_admin(client)
    created = _create_member(client)
    assert created["role"] == "household_member"
    assert "password_hash" not in created
    assert "mfa_secret" not in created

    listing = client.get("/api/household/members")
    assert listing.status_code == 200
    assert len(listing.json()) == 2

    updated = client.put(f"/api/household/members/{created['user_id']}", json={"display_name": "Kristy Williams", "role": "read_only"})
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Kristy Williams"
    assert updated.json()["role"] == "read_only"

    deactivated = client.post(f"/api/household/members/{created['user_id']}/deactivate")
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    reactivated = client.post(f"/api/household/members/{created['user_id']}/reactivate")
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_only_active_administrator_cannot_be_demoted_or_deactivated(client):
    admin = _setup_admin(client)
    assert client.put(f"/api/household/members/{admin['id']}", json={"role": "household_member"}).status_code == 409
    assert client.post(f"/api/household/members/{admin['id']}/deactivate").status_code == 409


def test_temporary_password_member_must_change_password(client):
    _setup_admin(client)
    member = _create_member(client)
    client.post("/api/auth/logout")
    login = client.post("/api/auth/login", json={"username": "kristy", "password": "Temporary123!"})
    assert login.status_code == 200
    security = client.get("/api/household/me/security")
    assert security.status_code == 200
    assert security.json()["must_change_password"] is True
    changed = client.post("/api/household/me/change-temporary-password", json={"new_password": "Permanent123!"})
    assert changed.status_code == 200
    assert client.get("/api/household/me/security").json()["must_change_password"] is False
    assert member["user_id"] > 0


def test_admin_password_reset_revokes_member_sessions(client):
    _setup_admin(client)
    member = _create_member(client)
    reset = client.post(f"/api/household/members/{member['user_id']}/password-reset", json={"temporary_password": "Reset123!"})
    assert reset.status_code == 200
    assert reset.json()["must_change_password"] is True


def test_mfa_reset_does_not_return_secret(client):
    _setup_admin(client)
    member = _create_member(client)
    reset = client.post(f"/api/household/members/{member['user_id']}/mfa-reset")
    assert reset.status_code == 200
    assert "secret" not in reset.json()
    assert reset.json()["mfa_enabled"] is False


def test_account_ownership_can_be_managed_by_admin(client):
    admin = _setup_admin(client)
    member = _create_member(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"}).json()
    ownership = client.get(f"/api/household/ownership/accounts/{account['id']}")
    assert ownership.status_code == 200
    assert ownership.json()["owner_user_id"] == admin["id"]
    updated = client.put(f"/api/household/ownership/accounts/{account['id']}", json={"owner_user_id": member["user_id"], "visibility": "household_shared"})
    assert updated.status_code == 200
    assert updated.json()["owner_user_id"] == member["user_id"]


def test_household_member_cannot_manage_members(client):
    _setup_admin(client)
    _create_member(client)
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "kristy", "password": "Temporary123!"})
    client.post("/api/household/me/change-temporary-password", json={"new_password": "Permanent123!"})
    response = client.post("/api/household/members", json={"username": "lee", "display_name": "Lee", "role": "household_member", "temporary_password": "Temporary123!"})
    assert response.status_code == 403


def test_household_context_is_derived_from_authenticated_membership(client):
    _setup_admin(client)
    household = client.get("/api/household/current").json()
    assert household["id"] > 0
    assert household["role"] == "administrator"
