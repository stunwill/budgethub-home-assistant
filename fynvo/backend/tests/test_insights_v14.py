from datetime import timedelta

from app.database import get_session_factory
from app.security import utcnow
from sqlalchemy import text


def setup_user(client):
    client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )


def add_account(client, balance="5000"):
    return client.post(
        "/api/accounts",
        json={"name": "Everyday", "account_type": "transaction", "opening_balance": balance},
    ).json()


def test_insights_are_protected(client):
    assert client.get("/api/insights").status_code == 401
    assert client.get("/api/insights/financial-health").status_code == 401


def test_financial_health_is_transparent_and_schema_reaches_v12(client):
    setup_user(client)
    add_account(client)
    response = client.get("/api/insights/financial-health?horizon_days=90")
    assert response.status_code == 200
    payload = response.json()
    assert "dimensions" in payload
    assert "cash_flow" in payload["dimensions"]
    assert "score" not in payload
    assert "opaque overall score" in payload["calculation"]

    with get_session_factory()() as db:
        assert db.execute(text("SELECT max(version) FROM schema_version")).scalar() >= 12


def test_cash_shortfall_insight_matches_forecast_and_has_evidence(client):
    setup_user(client)
    add_account(client, "100")
    tomorrow = (utcnow().date() + timedelta(days=1)).isoformat()
    client.post(
        "/api/planned-spending",
        json={
            "name": "Urgent repair",
            "estimated_amount": "600",
            "planned_date": tomorrow,
            "status": "committed",
            "include_in_forecast": True,
        },
    )
    forecast = client.get("/api/forecast?horizon=30d&mode=expected").json()
    assert forecast["shortfall"] is not None

    insights = client.get("/api/insights?horizon_days=30").json()
    cash = next(item for item in insights if item["insight_type"] == "cash_shortfall")
    assert cash["importance"] == "warning"
    assert cash["evidence"]["shortfall_date"] == forecast["shortfall"]["date"]
    assert cash["evidence"]["shortfall_balance"] == forecast["shortfall"]["balance"]
    assert cash["action_target"] == "Cash Flow"


def test_budget_projected_over_insight_reuses_budget_analysis(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date().isoformat()
    category = client.post("/api/categories", json={"name": "Groceries", "category_type": "expense"}).json()
    client.post(
        "/api/budgets",
        json={
            "name": "Groceries",
            "category_id": category["id"],
            "category_name": "Groceries",
            "period": "monthly",
            "amount": "100",
            "start_date": today,
        },
    )
    client.post(
        "/api/transactions",
        json={
            "account_id": account["id"],
            "date": today,
            "amount": "140",
            "transaction_type": "expense",
            "description": "Supermarket",
            "category": "Groceries",
        },
    )
    analysis = client.get("/api/budgets/analysis").json()
    budget_row = analysis["budgets"][0]
    assert float(budget_row["projected_variance"]) > 0

    insights = client.get("/api/insights").json()
    item = next(row for row in insights if row["insight_type"] == "budget_projected_over")
    assert item["related_entity_type"] == "budget"
    assert item["evidence"]["forecast"] == budget_row["forecast"]
    assert item["evidence"]["projected_variance"] == budget_row["projected_variance"]


def test_spending_trend_is_explainable_and_respects_comparable_windows(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date()
    for index in range(4):
        client.post(
            "/api/transactions",
            json={
                "account_id": account["id"],
                "date": (today - timedelta(days=7 * index)).isoformat(),
                "amount": "100",
                "transaction_type": "expense",
                "description": f"Recent groceries {index}",
                "category": "Groceries",
            },
        )
        client.post(
            "/api/transactions",
            json={
                "account_id": account["id"],
                "date": (today - timedelta(days=63 + 7 * index)).isoformat(),
                "amount": "50",
                "transaction_type": "expense",
                "description": f"Older groceries {index}",
                "category": "Groceries",
            },
        )

    insights = client.get("/api/insights").json()
    trend = next(row for row in insights if row["insight_type"] == "category_spending_trend" and row["evidence"]["category"] == "Groceries")
    assert trend["evidence"]["current_transactions"] >= 3
    assert trend["evidence"]["previous_transactions"] >= 3
    assert trend["evidence"]["percent_change"] > 0
    assert "rolling 8-week average" in trend["summary"]


def test_dismissed_identical_insight_does_not_reappear(client):
    setup_user(client)
    add_account(client, "100")
    tomorrow = (utcnow().date() + timedelta(days=1)).isoformat()
    client.post(
        "/api/planned-spending",
        json={"name": "Repair", "estimated_amount": "600", "planned_date": tomorrow, "status": "committed", "include_in_forecast": True},
    )
    rows = client.get("/api/insights?horizon_days=30").json()
    item = next(row for row in rows if row["insight_type"] == "cash_shortfall")
    assert client.post(f"/api/insights/{item['id']}/dismiss").status_code == 200

    refreshed = client.get("/api/insights?horizon_days=30").json()
    assert all(row["id"] != item["id"] for row in refreshed)
    history = client.get("/api/insights?status=dismissed&refresh=false").json()
    assert any(row["id"] == item["id"] for row in history)


def test_resolved_insight_leaves_active_dashboard_when_condition_clears(client):
    setup_user(client)
    add_account(client, "100")
    tomorrow = (utcnow().date() + timedelta(days=1)).isoformat()
    planned = client.post(
        "/api/planned-spending",
        json={"name": "Repair", "estimated_amount": "600", "planned_date": tomorrow, "status": "committed", "include_in_forecast": True},
    ).json()
    rows = client.get("/api/insights?horizon_days=30").json()
    item = next(row for row in rows if row["insight_type"] == "cash_shortfall")

    client.put(
        f"/api/planned-spending/{planned['id']}",
        json={"name": "Repair", "estimated_amount": "600", "planned_date": tomorrow, "status": "cancelled", "include_in_forecast": False},
    )
    client.get("/api/insights?horizon_days=30")
    history = client.get("/api/insights?status=resolved&refresh=false").json()
    assert any(row["id"] == item["id"] for row in history)

    dashboard = client.get("/api/dashboard/command-centre?range_days=30").json()
    assert all(row["id"] != item["id"] for row in dashboard["attention"]["top"])


def test_data_quality_insight_reports_uncategorised_transactions(client):
    setup_user(client)
    account = add_account(client)
    today = utcnow().date().isoformat()
    for index in range(3):
        client.post(
            "/api/transactions",
            json={
                "account_id": account["id"],
                "date": today,
                "amount": str(20 + index),
                "transaction_type": "expense",
                "description": f"Unknown merchant {index}",
            },
        )
    rows = client.get("/api/insights").json()
    quality = next(row for row in rows if row["insight_type"] == "uncategorised_transactions")
    assert quality["evidence"]["transaction_count"] == 3
    assert quality["action_target"] == "Transactions"
