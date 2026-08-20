from app.database import get_engine
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def category_by_path(client, path):
    return next(row for row in client.get("/api/categories").json() if row["path"] == path and row["is_active"])


def test_api_prevents_duplicate_parent_and_child_categories(client):
    setup_user(client)
    entertainment = category_by_path(client, "Entertainment")

    duplicate_parent = client.post("/api/categories", json={"name": " entertainment "})
    assert duplicate_parent.status_code == 409

    duplicate_child = client.post(
        "/api/categories",
        json={"name": " streaming ", "parent_id": entertainment["id"]},
    )
    assert duplicate_child.status_code == 409


def test_category_summary_consolidates_historical_duplicate_hierarchy_and_preserves_links(client):
    setup_user(client)
    entertainment = category_by_path(client, "Entertainment")
    streaming = category_by_path(client, "Entertainment → Streaming")

    account = client.post(
        "/api/accounts",
        json={"name": "Main", "account_type": "transaction", "opening_balance": "100.00"},
    ).json()
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Duplicate-linked streaming service",
            "amount": "24.49",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "account_id": account["id"],
            "category_id": streaming["id"],
        },
    )
    assert recurring.status_code == 201
    recurring_id = recurring.json()["id"]

    engine = get_engine()
    with engine.begin() as connection:
        now = "2026-08-20 00:00:00"
        connection.execute(
            text("""
                INSERT INTO categories(
                    user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at
                )
                VALUES(1,'Entertainment',NULL,'expense','independent',1,:now,:now)
            """),
            {"now": now},
        )
        duplicate_parent_id = int(connection.execute(text("SELECT last_insert_rowid()")).scalar())
        connection.execute(
            text("""
                INSERT INTO categories(
                    user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at
                )
                VALUES(1,'Streaming',:parent_id,'expense','independent',1,:now,:now)
            """),
            {"parent_id": duplicate_parent_id, "now": now},
        )
        duplicate_child_id = int(connection.execute(text("SELECT last_insert_rowid()")).scalar())
        connection.execute(
            text("""
                UPDATE recurring_expenses
                SET category_id=:category_id, category='Entertainment → Streaming'
                WHERE id=:recurring_id AND user_id=1
            """),
            {"category_id": duplicate_child_id, "recurring_id": recurring_id},
        )

    summary = client.get("/api/corrective-v0174/categories/summary?range_days=90")
    assert summary.status_code == 200

    active_categories = [row for row in client.get("/api/categories").json() if row["is_active"]]
    entertainment_rows = [row for row in active_categories if row["parent_id"] is None and row["name"].casefold() == "entertainment"]
    assert len(entertainment_rows) == 1
    canonical_parent_id = entertainment_rows[0]["id"]
    assert canonical_parent_id == entertainment["id"]

    streaming_rows = [
        row for row in active_categories
        if row["parent_id"] == canonical_parent_id and row["name"].casefold() == "streaming"
    ]
    assert len(streaming_rows) == 1
    assert streaming_rows[0]["id"] == streaming["id"]

    reloaded = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring_id)
    assert reloaded["category_id"] == streaming["id"]
    assert reloaded["category"] == "Entertainment → Streaming"

    entertainment_summary = next(
        row for row in summary.json()
        if row["id"] == entertainment["id"]
    )
    assert float(entertainment_summary["total"]) >= 24.49
