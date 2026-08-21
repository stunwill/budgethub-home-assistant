from sqlalchemy import text

from app.database import get_engine
from app.v13_cashflow import run_v13_migrations


def test_v144_repairs_legacy_cashflow_columns(client):
    setup = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert setup.status_code == 201

    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000.00"},
    )
    assert account.status_code == 201

    bill = client.post(
        "/api/bills",
        json={"name": "Legacy bill", "amount": "125.00", "due_date": "2026-08-21"},
    )
    assert bill.status_code == 201

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE bills DROP COLUMN remaining_amount_cents"))
        connection.execute(text("ALTER TABLE bills DROP COLUMN paid_at"))
        connection.execute(text("ALTER TABLE bills DROP COLUMN resolved_at"))

    run_v13_migrations(engine)

    with engine.begin() as connection:
        bill_columns = {
            row["name"]
            for row in connection.execute(text("PRAGMA table_info(bills)")).mappings().all()
        }
        assert {"remaining_amount_cents", "paid_at", "resolved_at"} <= bill_columns
        remaining = connection.execute(
            text("SELECT remaining_amount_cents FROM bills WHERE name='Legacy bill'")
        ).scalar()
        assert remaining == 12500

    response = client.get("/api/v1.3/cash-flow?horizon=30d&mode=expected")
    assert response.status_code == 200
    payload = response.json()
    assert payload["starting_balance"] == "1000.00"
