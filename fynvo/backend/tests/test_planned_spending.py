def setup_user(client):
    return client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def test_planned_spending_apis_are_protected(client):
    assert client.get("/api/planned-spending").status_code == 401
    assert client.post("/api/planned-spending", json={"name": "TV"}).status_code == 401


def test_create_edit_cancel_and_incomplete_planned_spending(client):
    setup_user(client)
    incomplete = client.post("/api/planned-spending", json={"name": "New Laptop", "status": "wishlist", "include_in_forecast": False})
    assert incomplete.status_code == 201
    assert incomplete.json()["estimated_amount"] is None
    assert incomplete.json()["completeness"] == "incomplete"
    created = client.post("/api/planned-spending", json={"name": "New TV", "estimated_amount": "2000", "planned_date": "2026-11-15", "category": "Planned Spending", "priority": "high", "status": "planned", "include_in_forecast": True})
    assert created.status_code == 201
    item = created.json()
    assert item["priority"] == "high"
    assert item["status"] == "planned"
    assert item["include_in_forecast"] is True
    edited = client.put(f"/api/planned-spending/{item['id']}", json={"estimated_amount": "1849", "status": "committed"})
    assert edited.status_code == 200
    assert edited.json()["estimated_amount"] == "1849.00"
    assert edited.json()["status"] == "committed"
    cancelled = client.post(f"/api/planned-spending/{item['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["include_in_forecast"] is False


def test_include_in_forecast_controls_schedule_totals(client):
    setup_user(client)
    client.post("/api/planned-spending", json={"name": "Japan Trip", "estimated_amount": "3500", "planned_date": "2026-10-10", "category": "Planned Spending", "status": "planned", "priority": "high", "include_in_forecast": True})
    client.post("/api/planned-spending", json={"name": "Wishlist BBQ", "estimated_amount": "1200", "planned_date": "2026-10-12", "category": "Planned Spending", "status": "wishlist", "priority": "medium", "include_in_forecast": True})
    client.post("/api/planned-spending", json={"name": "Excluded Laptop", "estimated_amount": "2400", "planned_date": "2026-10-15", "category": "Planned Spending", "status": "planned", "priority": "medium", "include_in_forecast": False})
    schedule = client.get("/api/schedule?start=2026-10-01&end=2026-10-31").json()
    names = {event["name"] for event in schedule["events"]}
    assert "Japan Trip" in names
    assert "Wishlist BBQ" not in names
    assert "Excluded Laptop" not in names
    assert schedule["planned_spending"] == "3500.00"


def test_month_week_matrix_and_year_matrix_include_planned_spending(client):
    setup_user(client)
    client.post("/api/planned-spending", json={"name": "Garage Door Rollers", "estimated_amount": "250", "planned_date": "2026-08-31", "category": "Planned Spending", "status": "committed", "priority": "medium", "include_in_forecast": True})
    matrix = client.get("/api/schedule/month/2026/8").json()
    assert len(matrix["weeks"]) in {5, 6}
    planned_rows = [row for row in matrix["rows"] if row["item"] == "Garage Door Rollers"]
    assert planned_rows
    assert planned_rows[0]["month_total"] == "-250.00"
    assert any(cell["items"] for cell in planned_rows[0]["weeks"])
    year = client.get("/api/schedule/year/2026").json()
    assert any(row["item"] == "Garage Door Rollers" for row in year["rows"])


def test_dashboard_planned_spending_uses_real_data(client):
    setup_user(client)
    client.post("/api/planned-spending", json={"name": "New BBQ", "estimated_amount": "1200", "planned_date": "2026-09-20", "category": "Planned Spending", "status": "planned", "priority": "medium", "include_in_forecast": True})
    dashboard = client.get("/api/dashboard/overview").json()
    assert dashboard["summary"]["planned_item_count"] == 1
    assert dashboard["summary"]["planned_spending"] == "1200.00"
    assert dashboard["top_planned_spending"][0]["name"] == "New BBQ"
