from datetime import timedelta

from app.security import utcnow


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code in {200, 201}


def add_account(client, balance="5000"):
    response = client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": balance},
    )
    assert response.status_code == 201
    return response.json()


def test_recurring_commitment_monthly_and_annual_equivalents(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date().isoformat()
    response = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Weekly commitment",
            "amount": "100.00",
            "frequency": "weekly",
            "next_due_date": today,
            "account_id": account["id"],
            "category": "Household",
        },
    )
    assert response.status_code == 201

    refreshed = client.post("/api/insights/refresh?horizon_days=90")
    assert refreshed.status_code == 200
    recurring = refreshed.json()["recurring_commitments"]
    assert recurring["count"] == 1
    assert recurring["monthly_equivalent"] == "433.33"
    assert recurring["annual_equivalent"] == "5199.96"
    assert recurring["items"][0]["name"] == "Weekly commitment"


def test_savings_rate_excludes_refund_income_and_transfer_transaction_types(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date().isoformat()

    salary = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "date": today,
            "amount": "1000.00",
            "transaction_type": "income",
            "description": "Salary",
            "category": "Income",
        },
    )
    assert salary.status_code == 201
    refund = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "date": today,
            "amount": "100.00",
            "transaction_type": "income",
            "description": "Store refund",
            "category": "Refund",
        },
    )
    assert refund.status_code == 201
    expense = client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "date": today,
            "amount": "600.00",
            "transaction_type": "expense",
            "description": "Groceries",
            "category": "Groceries",
        },
    )
    assert expense.status_code == 201

    refreshed = client.post("/api/insights/refresh?horizon_days=90").json()
    savings = refreshed["savings"]
    assert savings["actual_income"] == "1000.00"
    assert savings["actual_expense"] == "600.00"
    assert savings["net_savings"] == "400.00"
    assert savings["savings_rate_percent"] == 40.0
    assert savings["reliable"] is True


def test_savings_rate_is_suppressed_without_income(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date().isoformat()
    client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "date": today,
            "amount": "25.00",
            "transaction_type": "expense",
            "description": "Coffee",
            "category": "Dining",
        },
    )
    savings = client.post("/api/insights/refresh?horizon_days=90").json()["savings"]
    assert savings["reliable"] is False
    assert savings["savings_rate_percent"] is None


def test_goal_behind_insight_uses_goal_service_values(client):
    setup_user(client)
    add_account(client)
    today = utcnow().date()
    response = client.post(
        "/api/goals",
        json={
            "name": "Holiday",
            "goal_type": "savings",
            "target_amount": "2400.00",
            "current_amount": "0.00",
            "start_date": (today - timedelta(days=180)).isoformat(),
            "target_date": (today + timedelta(days=60)).isoformat(),
            "contribution_frequency": "monthly",
            "contribution_amount": "100.00",
            "priority": "medium",
            "status": "active",
        },
    )
    assert response.status_code == 201
    goal = response.json()
    assert goal["progress"]["status"] == "behind"

    rows = client.get("/api/insights?horizon_days=90").json()
    insight = next(item for item in rows if item["insight_type"] == "goal_behind")
    assert insight["related_entity_id"] == goal["id"]
    assert insight["evidence"]["required_contribution"] == goal["progress"]["required_contribution"]
    assert insight["evidence"]["current_contribution"] == goal["progress"]["current_contribution"]
    assert insight["action_target"] == "Goals"


def test_active_scenario_generates_isolated_impact_insight(client):
    setup_user(client)
    add_account(client, "4000")
    today = utcnow().date()
    scenario = client.post(
        "/api/scenarios",
        json={"name": "New TV", "forecast_horizon": "90d", "status": "active"},
    )
    assert scenario.status_code == 201
    scenario_id = scenario.json()["id"]
    adjustment = client.post(
        f"/api/scenarios/{scenario_id}/adjustments",
        json={
            "kind": "one_off_expense",
            "name": "New TV",
            "amount": "1200.00",
            "effective_from": (today + timedelta(days=10)).isoformat(),
            "category": "Entertainment",
        },
    )
    assert adjustment.status_code == 201

    rows = client.get("/api/insights?horizon_days=90").json()
    insight = next(item for item in rows if item["insight_type"] == "scenario_impact")
    assert insight["related_entity_id"] == scenario_id
    assert insight["evidence"]["isolated"] is True
    assert float(insight["evidence"]["end_balance_difference"]) < 0
    assert insight["action_target"] == "Scenarios"


def test_reviewed_status_and_filters(client):
    setup_user(client)
    add_account(client, "100")
    tomorrow = (utcnow().date() + timedelta(days=1)).isoformat()
    client.post(
        "/api/planned-spending",
        json={
            "name": "Repair",
            "estimated_amount": "600.00",
            "planned_date": tomorrow,
            "status": "committed",
            "include_in_forecast": True,
        },
    )
    rows = client.get("/api/insights?horizon_days=30").json()
    shortfall = next(item for item in rows if item["insight_type"] == "cash_shortfall")
    reviewed = client.post(f"/api/insights/{shortfall['id']}/reviewed")
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"

    warning_rows = client.get("/api/insights?importance=warning&refresh=false").json()
    assert warning_rows
    assert all(item["importance"] == "warning" for item in warning_rows)
    cash_rows = client.get("/api/insights?category=cash_flow&refresh=false").json()
    assert cash_rows
    assert all(item["category"] == "cash_flow" for item in cash_rows)


def test_dashboard_limits_priority_insights_to_three(client):
    setup_user(client)
    account = add_account(client, "100")
    today = utcnow().date()
    # Create enough data-quality and forecast conditions to populate attention without flooding Overview.
    for index in range(12):
        client.post(
            "/api/transactions",
            json={
                "account_id": account["id"],
                "date": today.isoformat(),
                "amount": "10.00",
                "transaction_type": "expense",
                "description": f"Unknown {index}",
            },
        )
    client.post(
        "/api/planned-spending",
        json={
            "name": "Repair",
            "estimated_amount": "600.00",
            "planned_date": (today + timedelta(days=1)).isoformat(),
            "status": "committed",
            "include_in_forecast": True,
        },
    )
    dashboard = client.get("/api/dashboard/command-centre?range_days=30")
    assert dashboard.status_code == 200
    attention = dashboard.json()["attention"]
    assert len(attention["top"]) <= 3
    assert attention["insights"] >= len(attention["top"])
