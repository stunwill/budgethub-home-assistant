from app.config import APP_VERSION
from app.database import get_engine, run_migrations
from sqlalchemy import text


def setup_user(client):
    response = client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    assert response.status_code == 201


def test_account_creation_balance_edit_archive_and_inactive_transaction_block(client):
    setup_user(client)
    created = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00", "institution": "ING"})
    assert created.status_code == 201
    account = created.json()
    assert account["current_balance"] == "1000.00"
    edited = client.put(f"/api/accounts/{account['id']}", json={"name": "Main Everyday", "description": "Bills"})
    assert edited.status_code == 200
    assert edited.json()["name"] == "Main Everyday"
    archived = client.delete(f"/api/accounts/{account['id']}")
    assert archived.status_code == 200
    blocked = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "10.00", "transaction_type": "expense", "description": "Coffee"})
    assert blocked.status_code == 409


def test_expense_and_income_transaction_signs_running_balance_and_edit_history(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    expense = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "100.00", "transaction_type": "expense", "description": "Groceries"})
    assert expense.status_code == 201
    income = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-18", "amount": "500.00", "transaction_type": "income", "description": "Pay"})
    assert income.status_code == 201
    rows = client.get(f"/api/accounts/{account['id']}/transactions").json()
    assert rows[0]["running_balance"] == "900.00"
    assert rows[1]["running_balance"] == "1400.00"
    updated = client.put(f"/api/transactions/{expense.json()['id']}", json={"amount": "120.00"})
    assert updated.status_code == 200
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM edit_history WHERE record_type='transactions'")).scalar() >= 1


def test_transfer_creates_linked_transactions_and_household_net_zero(client):
    setup_user(client)
    first = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    second = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "500.00"}).json()
    transfer = client.post("/api/transfers", json={"from_account_id": first["id"], "to_account_id": second["id"], "date": "2026-08-17", "amount": "200.00", "description": "Savings"})
    assert transfer.status_code == 201
    with get_engine().connect() as connection:
        rows = connection.execute(text("SELECT account_id, amount_cents, transfer_id FROM transactions WHERE transfer_id=:id ORDER BY account_id"), {"id": transfer.json()["id"]}).mappings().all()
    assert len(rows) == 2
    assert sum(row["amount_cents"] for row in rows) == 0


def test_transaction_delete_and_transfer_delete(client):
    setup_user(client)
    first = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    second = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "0.00"}).json()
    tx = client.post("/api/transactions", json={"account_id": first["id"], "date": "2026-08-17", "amount": "20.00", "transaction_type": "expense", "description": "Coffee"}).json()
    assert client.delete(f"/api/transactions/{tx['id']}").status_code == 200
    transfer = client.post("/api/transfers", json={"from_account_id": first["id"], "to_account_id": second["id"], "date": "2026-08-17", "amount": "100.00", "description": "Move"}).json()
    assert client.delete(f"/api/transfers/{transfer['id']}").status_code == 200


def test_account_detail_v09_contract(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    detail = client.get(f"/api/accounts/{account['id']}")
    assert detail.status_code == 200
    assert detail.json()["account"]["name"] == "Everyday"


def test_account_meta_and_dashboard_position(client):
    setup_user(client)
    client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"})
    client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "500.00"})
    meta = client.get("/api/accounts/meta")
    assert meta.status_code == 200
    assert "transaction" in meta.json()["account_types"]
    position = client.get("/api/dashboard/position")
    assert position.status_code == 200
    assert position.json()["net_position"] == "1500.00"


def test_account_update_prevents_invalid_account_type(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "0.00"}).json()
    response = client.put(f"/api/accounts/{account['id']}", json={"account_type": "not_real"})
    assert response.status_code == 400


def test_transfer_update_replaces_linked_transactions(client):
    setup_user(client)
    first = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    second = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "0.00"}).json()
    transfer = client.post("/api/transfers", json={"from_account_id": first["id"], "to_account_id": second["id"], "date": "2026-08-17", "amount": "100.00", "description": "Move"}).json()
    updated = client.put(f"/api/transfers/{transfer['id']}", json={"amount": "150.00", "description": "Move more"})
    assert updated.status_code == 200
    with get_engine().connect() as connection:
        rows = connection.execute(text("SELECT amount_cents FROM transactions WHERE transfer_id=:id"), {"id": transfer["id"]}).scalars().all()
    assert sorted(rows) == [-15000, 15000]


def test_transaction_cannot_delete_transfer_leg(client):
    setup_user(client)
    first = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    second = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "0.00"}).json()
    transfer = client.post("/api/transfers", json={"from_account_id": first["id"], "to_account_id": second["id"], "date": "2026-08-17", "amount": "100.00", "description": "Move"}).json()
    with get_engine().connect() as connection:
        tx_id = connection.execute(text("SELECT id FROM transactions WHERE transfer_id=:id LIMIT 1"), {"id": transfer["id"]}).scalar()
    assert client.delete(f"/api/transactions/{tx_id}").status_code == 400


def test_liability_account_semantics(client):
    setup_user(client)
    card = client.post("/api/accounts", json={"name": "Credit Card", "account_type": "credit_card", "opening_balance": "0.00"}).json()
    assert card["account_class"] == "liability"
    client.post("/api/transactions", json={"account_id": card["id"], "date": "2026-08-17", "amount": "100.00", "transaction_type": "expense", "description": "Purchase"})
    assert client.get(f"/api/accounts/{card['id']}").json()["account"]["current_balance"] == "100.00"


def test_account_meta_exposes_pre_v1_supported_types(client):
    setup_user(client)
    types = set(client.get("/api/accounts/meta").json()["account_types"])
    assert {"transaction", "savings", "offset", "credit_card", "cash", "mortgage", "personal_loan", "car_loan", "line_of_credit", "investment", "superannuation", "other_asset", "other_liability"}.issubset(types)


def test_migration_schema_version_thirteen(client):
    run_migrations()
    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 13


def test_home_assistant_spa_routes_and_api_protection(client):
    assert client.get("/api/health").json()["version"] == APP_VERSION
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/accounts").status_code == 200
    assert client.get("/api/accounts").status_code == 401
