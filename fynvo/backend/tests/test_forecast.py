from datetime import timedelta

from app.forecast import today_local


def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_forecast_apis_are_protected(client):
    assert client.get("/api/forecast").status_code == 401
    assert client.post("/api/effective-amount-changes", json={}).status_code == 401
    assert client.post("/api/forecast/scenario", json={}).status_code == 401


def test_baseline_forecast_uses_income_recurring_bills_and_planned_spending(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"}).json()
    client.post("/api/income", json={"name": "Salary", "amount": "500", "frequency": "weekly", "next_payment_date": "2026-08-17", "destination_account_id": account["id"], "category": "Income"})
    client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "100", "frequency": "weekly", "next_due_date": "2026-08-18", "account_id": account["id"], "category": "Utilities"})
    client.post("/api/bills", json={"name": "Dentist", "amount": "120", "due_date": "2026-08-19", "account_id": account["id"], "bill_type": "Health"})
    client.post("/api/planned-spending", json={"name": "Tyres", "estimated_amount": "300", "planned_date": "2026-08-20", "status": "planned", "category": "Transport", "include_in_forecast": True})
    forecast = client.get("/api/forecast?horizon=7d&start=2026-08-16").json()
    names = [event["name"] for event in forecast["events"]]
    assert "Salary" in names
    assert "Internet" in names
    assert "Dentist" in names
    assert "Tyres" in names
    assert forecast["starting_balance"] == "1000.00"
    assert forecast["final_balance"] == "980.00"
    assert forecast["lowest_balance"]["balance"] == "980.00"


def test_effective_dated_changes_apply_only_from_effective_date(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"}).json()
    recurring = client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "140", "frequency": "monthly", "next_due_date": "2026-09-01", "account_id": account["id"], "category": "Utilities"}).json()
    change = client.post("/api/effective-amount-changes", json={"record_type": "recurring_expense", "record_id": recurring["id"], "new_amount": "80", "effective_from": "2026-10-01", "notes": "New plan"})
    assert change.status_code == 201
    forecast = client.get("/api/forecast?horizon=90d&start=2026-09-01").json()
    amounts = [(event["date"], event["amount"]) for event in forecast["events"] if event["name"] == "Internet"]
    assert ("2026-09-01", "-140.00") in amounts
    assert ("2026-10-01", "-80.00") in amounts
    assert ("2026-11-01", "-80.00") in amounts


def test_expected_forecast_uses_run_rate_without_double_counting_known_categories(client):
    setup_user(client)
    account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "2000"}).json()
    start = today_local()
    for weeks_ago in range(1, 9):
        day = start - timedelta(days=weeks_ago * 7)
        client.post("/api/transactions", json={"account_id": account["id"], "date": day.isoformat(), "amount": "100", "transaction_type": "expense", "description": "Woolworths", "category": "Groceries"})
    client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "80", "frequency": "weekly", "next_due_date": start.isoformat(), "account_id": account["id"], "category": "Utilities"})
    forecast = client.get("/api/forecast?horizon=30d&mode=expected").json()
    assert any(event["source_type"] == "run_rate_estimate" and event["category"] == "Groceries" for event in forecast["events"])
    assert not any(event["source_type"] == "run_rate_estimate" and event["category"] == "Utilities" for event in forecast["events"])


def test_shortfall_and_scenario_are_calculated_without_mutating_records(client):
    setup_user(client)
    client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "100"}).json()
    client.post("/api/planned-spending", json={"name": "Car Repair", "estimated_amount": "500", "planned_date": "2026-08-20", "status": "committed", "category": "Transport", "include_in_forecast": True})
    forecast = client.get("/api/forecast?horizon=7d&start=2026-08-16").json()
    assert forecast["shortfall"]["date"] == "2026-08-20"
    scenario_date = (today_local() + timedelta(days=1)).isoformat()
    scenario = client.post("/api/forecast/scenario", json={"name": "Extra income", "horizon": "7d", "mode": "baseline", "adjustments": [{"kind": "one_off_income", "name": "Sale", "amount": "600", "date": scenario_date}]}).json()
    assert scenario["isolated"] is True
    assert scenario["difference"] == "600.00"
    planned = client.get("/api/planned-spending").json()
    assert len([row for row in planned if row["name"] == "Car Repair"]) == 1


def test_forecast_schema_version_and_drilldown(client):
    setup_user(client)
    forecast = client.get("/api/forecast?horizon=7d").json()
    assert "chart_points" in forecast
    drilldown = client.get("/api/forecast/drilldown?period=month&horizon=30d").json()
    assert drilldown["period"] == "month"
