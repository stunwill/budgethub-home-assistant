from app.database import get_engine, run_migrations
from app.money import parse_money
from sqlalchemy import text


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_accounts_transactions_balances_and_running_balance(client):
    assert client.get("/api/accounts").status_code == 401
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    assert account["current_balance"] == "1000.00"
    income = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "2850.00", "transaction_type": "income", "description": "Salary"}).json()
    assert income["amount"] == "2850.00"
    expense = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-18", "amount": "142.36", "transaction_type": "expense", "description": "Woolworths"}).json()
    assert expense["amount"] == "-142.36"
    detail = client.get(f"/api/accounts/{account['id']}").json()
    assert detail["account"]["current_balance"] == "3707.64"
    assert detail["transactions"][-1]["running_balance"] == "3707.64"


def test_historical_insert_and_edit_recalculate_balance(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "100.00"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-20", "amount": "50.00", "transaction_type": "expense", "description": "Later"})
    tx = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "20.00", "transaction_type": "income", "description": "Earlier"}).json()
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "70.00"
    client.put(f"/api/transactions/{tx['id']}", json={"amount": "40.00"})
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "90.00"


def test_transfers_update_both_accounts_without_income_or_expense(client):
    setup_user(client)
    everyday = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"}).json()
    savings = client.post("/api/accounts", json={"name": "Savings", "account_type": "savings", "opening_balance": "100.00"}).json()
    transfer = client.post("/api/transfers", json={"from_account_id": everyday["id"], "to_account_id": savings["id"], "date": "2026-08-17", "amount": "500.00", "description": "Move to savings"}).json()
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "500.00"
    assert client.get(f"/api/accounts/{savings['id']}").json()["account"]["current_balance"] == "600.00"
    client.put(f"/api/transfers/{transfer['id']}", json={"amount": "200.00"})
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "800.00"
    assert client.get(f"/api/accounts/{savings['id']}").json()["account"]["current_balance"] == "300.00"
    txs = client.get("/api/transactions").json()
    assert {tx["transaction_type"] for tx in txs} == {"transfer"}
    client.delete(f"/api/transfers/{transfer['id']}")
    assert client.get(f"/api/accounts/{everyday['id']}").json()["account"]["current_balance"] == "1000.00"


def test_archive_account_and_decimal_precision(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Cash", "account_type": "cash", "opening_balance": "0.10"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-17", "amount": "0.20", "transaction_type": "income", "description": "Coins"})
    assert parse_money("0.10") + parse_money("0.20") == 30
    assert client.get(f"/api/accounts/{account['id']}").json()["account"]["current_balance"] == "0.30"
    client.post(f"/api/accounts/{account['id']}/archive")
    assert client.get("/api/accounts").json() == []


def test_liability_account_semantics(client):
    setup_user(client)
    card = client.post("/api/accounts", json={"name": "Credit Card", "account_type": "credit_card", "opening_balance": "0.00"}).json()
    client.post("/api/transactions", json={"account_id": card["id"], "date": "2026-08-17", "amount": "100.00", "transaction_type": "expense", "description": "Purchase"})
    assert client.get(f"/api/accounts/{card['id']}").json()["account"]["current_balance"] == "100.00"


def test_migration_schema_version_eight(client):
    run_migrations()
    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 8


def test_home_assistant_spa_routes_and_api_protection(client):
    assert client.get("/api/health").json()["version"] == "0.14.0"
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/accounts").status_code == 200
    assert client.get("/api/accounts").status_code == 401
