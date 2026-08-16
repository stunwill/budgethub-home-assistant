def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_scheduled_finance_apis_are_protected(client):
    assert client.get("/api/income").status_code == 401
    assert client.get("/api/recurring-expenses").status_code == 401
    assert client.get("/api/bills").status_code == 401
    assert client.get("/api/schedule").status_code == 401


def test_seeded_recurring_expenses_include_incomplete_and_inactive_records(client):
    setup_user(client)
    rows = client.get("/api/recurring-expenses").json()
    names = {row["name"] for row in rows}
    assert "Home Loan" in names
    assert "Sienna's Savings" in names
    assert "Disney" in names
    sienna = next(row for row in rows if row["name"] == "Sienna's Savings")
    assert sienna["amount"] is None
    assert sienna["completeness"] == "incomplete"
    disney = next(row for row in rows if row["name"] == "Disney")
    assert disney["is_active"] is False
    assert disney["completeness"] == "inactive_incomplete"
    incomplete = client.get("/api/recurring-expenses?filter=incomplete").json()
    assert any(row["name"] == "Powershop" for row in incomplete)


def test_create_income_and_recurring_with_recurrence(client):
    setup_user(client)
    income = client.post("/api/income", json={"name": "Salary", "amount": "2100", "frequency": "fortnightly", "next_payment_date": "2026-08-20", "payer": "Employer"})
    assert income.status_code == 201
    assert income.json()["completeness"] == "incomplete"
    recurring = client.post("/api/recurring-expenses", json={"name": "Boost Phone", "amount": "28", "frequency": "every_28_days", "next_due_date": "2026-08-21", "source_account_text": "KW ING Everyday"})
    assert recurring.status_code == 201
    assert recurring.json()["frequency"] == "every_28_days"
    schedule = client.get("/api/schedule?view=month&start=2026-08-16&end=2026-09-30").json()
    assert any(event["name"] == "Salary" for event in schedule["events"])
    assert any(event["name"] == "Boost Phone" for event in schedule["events"])


def test_bills_overdue_unknown_amount_and_priority(client):
    setup_user(client)
    bills = client.get("/api/bills").json()
    water = next(row for row in bills if row["name"] == "Water Bill")
    assert water["status"] == "overdue"
    assert water["priority"] == "high"
    rates = next(row for row in bills if row["name"] == "Rates")
    assert rates["amount"] is None
    assert rates["status"] == "unknown"
    bill = client.post("/api/bills", json={"name": "Dentist", "amount": "120.10", "due_date": "2026-08-16", "priority": "normal"})
    assert bill.status_code == 201


def test_annual_matrix_contains_drilldown_items_and_no_zero_for_unknowns(client):
    setup_user(client)
    matrix = client.get("/api/schedule/year/2026").json()
    assert matrix["year"] == 2026
    netflix = [row for row in matrix["rows"] if row["item"] == "Netflix"]
    assert netflix
    august = netflix[0]["months"]["8"]
    assert august["items"]
    assert august["total"] != "0.00"


def test_dashboard_uses_v040_scheduled_data(client):
    setup_user(client)
    dashboard = client.get("/api/dashboard/overview").json()
    assert dashboard["summary"]["incomplete_recurring_count"] > 0
    assert dashboard["summary"]["bills_due_count"] > 0
    assert dashboard["upcoming"]
