from app.database import get_engine
from sqlalchemy import text


def setup_user(client):
    return client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )


def test_cashflow_repairs_missing_v13_account_buffer_schema(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"},
    )
    assert account.status_code == 201

    engine = get_engine()
    with engine.begin() as connection:
        columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(accounts)")).mappings().all()
        }
        assert "minimum_balance_cents" in columns
        connection.execute(text("ALTER TABLE accounts DROP COLUMN minimum_balance_cents"))

    response = client.get("/api/v1.3/cash-flow?horizon=7d")
    assert response.status_code == 200
    assert response.json()["starting_balance"] == "1000.00"

    with engine.begin() as connection:
        columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(accounts)")).mappings().all()
        }
        assert "minimum_balance_cents" in columns
