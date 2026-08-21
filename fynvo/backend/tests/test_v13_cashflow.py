from datetime import date


def setup_user(client):
    return client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )


def test_v13_cashflow_routes_are_protected(client):
    assert client.get("/api/v1.3/cash-flow").status_code == 401
    assert client.get("/api/v1.3/calendar").status_code == 401
    assert client.get("/api/v1.3/upcoming").status_code == 401
    assert client.post("/api/v1.3/purchase-simulator", json={}).status_code == 401


def test_internal_transfer_changes_accounts_but_not_household_total(client):
    setup_user(client)
    everyday = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"},
    ).json()
    savings = client.post(
        "/api/accounts",
        json={"name": "Savings", "account_type": "savings", "opening_balance": "500"},
    ).json()
    client.post(
        "/api/transfers",
        json={
            "from_account_id": everyday["id"],
            "to_account_id": savings["id"],
            "amount": "200",
            "date": "2026-08-22",
            "description": "Move to savings",
        },
    )
    result = client.get("/api/v1.3/cash-flow?horizon=7d&start=2026-08-21").json()
    assert result["starting_balance"] == "1500.00"
    assert result["final_balance"] == "1500.00"
    transfer = next(row for row in result["events"] if row["direction"] == "transfer")
    assert transfer["amount"] == "0.00"
    assert transfer["account_balances"][str(everyday["id"])] == "800.00"
    assert transfer["account_balances"][str(savings["id"])] == "700.00"


def test_overdue_bill_is_retained_in_forecast(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"},
    ).json()
    client.post(
        "/api/bills",
        json={
            "name": "Electricity",
            "amount": "237",
            "due_date": "2026-08-10",
            "account_id": account["id"],
            "bill_type": "Utilities",
        },
    )
    result = client.get("/api/v1.3/cash-flow?horizon=7d&start=2026-08-21").json()
    overdue = next(row for row in result["events"] if row["name"] == "Electricity")
    assert overdue["occurrence_status"] == "overdue"
    assert overdue["original_due_date"] == "2026-08-10"
    assert result["final_balance"] == "763.00"


def test_occurrence_override_does_not_modify_template(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "5000"},
    ).json()
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Mortgage",
            "amount": "2802",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "account_id": account["id"],
            "category": "Mortgage",
        },
    ).json()
    response = client.post(
        "/api/v1.3/occurrence-overrides",
        json={
            "source_type": "recurring_expense",
            "source_id": recurring["id"],
            "occurrence_date": "2026-09-01",
            "amount": "3000",
            "status": "due",
            "apply_future": False,
        },
    )
    assert response.status_code == 201
    forecast = client.get("/api/v1.3/cash-flow?horizon=60d&start=2026-09-01").json()
    mortgage = [row for row in forecast["events"] if row["name"] == "Mortgage"]
    assert mortgage[0]["amount"] == "-3000.00"
    assert mortgage[1]["amount"] == "-2802.00"
    template = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring["id"])
    assert template["amount"] == "2802.00"


def test_buffer_warning_and_purchase_simulation(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"},
    ).json()
    update = client.put(
        f"/api/v1.3/accounts/{account['id']}/buffer",
        json={"minimum_balance": "500"},
    )
    assert update.status_code == 200
    client.post(
        "/api/planned-spending",
        json={
            "name": "Rates",
            "estimated_amount": "650",
            "planned_date": "2026-08-25",
            "status": "committed",
            "account_id": account["id"],
            "include_in_forecast": True,
        },
    )
    result = client.get("/api/v1.3/cash-flow?horizon=7d&start=2026-08-21").json()
    warning = next(row for row in result["warnings"] if row["kind"] == "low_balance")
    assert warning["date"] == "2026-08-25"
    assert warning["projected_balance"] == "350.00"
    assert warning["shortfall"] == "150.00"

    simulation = client.post(
        "/api/v1.3/purchase-simulator",
        json={
            "amount": "400",
            "proposed_date": date(2026, 8, 22).isoformat(),
            "account_id": account["id"],
            "description": "Test purchase",
            "horizon": "7d",
        },
    ).json()
    assert simulation["isolated"] is True
    assert simulation["negative_balance_predicted"] is True
    assert simulation["buffer_breached"] is True


def test_calendar_has_daily_totals(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"},
    ).json()
    client.post(
        "/api/income",
        json={
            "name": "Salary",
            "amount": "1000",
            "frequency": "monthly",
            "next_payment_date": "2026-08-25",
            "destination_account_id": account["id"],
            "category": "Income",
        },
    )
    client.post(
        "/api/planned-spending",
        json={
            "name": "Rates",
            "estimated_amount": "300",
            "planned_date": "2026-08-25",
            "status": "committed",
            "account_id": account["id"],
            "include_in_forecast": True,
        },
    )
    calendar = client.get("/api/v1.3/calendar?start=2026-08-21&days=10").json()
    day = next(row for row in calendar["days"] if row["date"] == "2026-08-25")
    assert day["income"] == "1000.00"
    assert day["expenses"] == "300.00"
    assert day["net"] == "700.00"
