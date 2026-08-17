from app.database import get_engine
from app.finance import today_local
from sqlalchemy import text


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_mock_provider_connect_link_sync_idempotency_and_pending_to_posted(client):
    setup_user(client)
    providers = client.get("/api/bank-connections/providers")
    assert providers.status_code == 200
    assert providers.json()["providers"][0]["id"] == "mock_cdr"

    connected = client.post("/api/bank-connections/mock/connect", json={"institution_id": "mock-bank-au"})
    assert connected.status_code == 201
    connection = connected.json()
    assert connection["is_mock"] is True
    assert len(connection["accounts"]) == 3

    external = connection["accounts"][0]
    linked = client.post(f"/api/bank-connections/{connection['id']}/accounts/{external['id']}/link", json={})
    assert linked.status_code == 200
    assert linked.json()["fynvo_account_id"] is not None

    first_sync = client.post(f"/api/bank-connections/{connection['id']}/sync")
    assert first_sync.status_code == 200
    payload = first_sync.json()
    assert payload["added"] >= 1

    second_sync = client.post(f"/api/bank-connections/{connection['id']}/sync")
    assert second_sync.status_code == 200
    assert second_sync.json()["duplicates_ignored"] >= 1

    with get_engine().begin() as connection_db:
        assert connection_db.execute(text("SELECT max(version) FROM schema_version")).scalar() >= 11
        tx_count = connection_db.execute(text("SELECT count(*) FROM transactions WHERE source='bank_sync'")).scalar()
        identity_count = connection_db.execute(text("SELECT count(*) FROM bank_transaction_identities")).scalar()
        assert tx_count == identity_count


def test_disconnect_preserves_historical_transactions(client):
    setup_user(client)
    connected = client.post("/api/bank-connections/mock/connect", json={"institution_id": "mock-bank-au"}).json()
    external = connected["accounts"][0]
    client.post(f"/api/bank-connections/{connected['id']}/accounts/{external['id']}/link", json={})
    client.post(f"/api/bank-connections/{connected['id']}/sync")
    before = len(client.get("/api/transactions").json())
    disconnected = client.post(f"/api/bank-connections/{connected['id']}/disconnect")
    assert disconnected.status_code == 200
    assert disconnected.json()["status"] == "disconnected"
    after = len(client.get("/api/transactions").json())
    assert after == before


def test_dashboard_upcoming_commitments_and_overdue_are_separate(client):
    setup_user(client)
    current_day = today_local()
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000.00"}).json()
    client.post("/api/income", json={"name": "Salary", "amount": "2100.00", "frequency": "one_off", "next_payment_date": (current_day + __import__('datetime').timedelta(days=1)).isoformat(), "destination_account_id": account["id"]})
    client.post("/api/bills", json={"name": "Old Bill", "amount": "120.00", "due_date": (current_day - __import__('datetime').timedelta(days=1)).isoformat(), "account_id": account["id"]})
    client.post("/api/bills", json={"name": "Internet", "amount": "140.00", "due_date": (current_day + __import__('datetime').timedelta(days=4)).isoformat(), "account_id": account["id"]})
    dashboard = client.get("/api/dashboard/command-centre?range_days=90")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    upcoming_names = {item["name"] for item in payload["upcoming"]}
    commitment_names = {item["name"] for item in payload["upcoming_commitments"]}
    assert "Salary" in upcoming_names
    assert "Internet" in upcoming_names
    assert "Internet" in commitment_names
    assert "Salary" not in commitment_names
    assert "Old Bill" not in upcoming_names
    assert payload["overdue"]["count"] >= 1
    assert any(item["amount"].startswith("-") for item in payload["upcoming"] if item["name"] == "Internet")
    assert any(not item["amount"].startswith("-") for item in payload["upcoming"] if item["name"] == "Salary")
