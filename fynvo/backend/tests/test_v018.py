from app.database import get_engine
from app.v018 import dedupe_commitments, normalise_category_name
from sqlalchemy import text


def setup_user(client):
    response = client.post(
        "/api/auth/setup",
        json={"username": "stu", "display_name": "Stu", "password": "Password123!"},
    )
    assert response.status_code == 201


def active_category(client, path):
    return next(
        row
        for row in client.get("/api/categories").json()
        if row["path"] == path and row["is_active"]
    )


def test_category_normalisation_collapses_case_and_whitespace():
    assert normalise_category_name("  Home   Phone ") == "home phone"
    assert normalise_category_name("ENTERTAINMENT") == "entertainment"


def test_category_create_and_update_reject_normalised_duplicates(client):
    setup_user(client)
    entertainment = active_category(client, "Entertainment")
    utilities = active_category(client, "Utilities")

    parent_duplicate = client.post(
        "/api/categories",
        json={"name": "  entertainment   "},
    )
    assert parent_duplicate.status_code == 409

    child_duplicate = client.post(
        "/api/categories",
        json={"name": "  Home   Phone  ", "parent_id": utilities["id"]},
    )
    assert child_duplicate.status_code == 409

    custom = client.post(
        "/api/categories",
        json={"name": "Custom Media", "parent_id": entertainment["id"]},
    )
    assert custom.status_code == 201
    renamed = client.put(
        f"/api/categories/{custom.json()['id']}",
        json={"name": "  STREAMING  ", "parent_id": entertainment["id"]},
    )
    assert renamed.status_code == 409


def test_category_merge_preserves_references_and_archives_source(client):
    setup_user(client)
    source = client.post("/api/categories", json={"name": "Source Parent"}).json()
    destination = client.post("/api/categories", json={"name": "Destination Parent"}).json()
    source_child = client.post(
        "/api/categories",
        json={"name": "Shared Child", "parent_id": source["id"]},
    ).json()
    client.post(
        "/api/categories",
        json={"name": "Shared Child", "parent_id": destination["id"]},
    ).json()
    account = client.post(
        "/api/accounts",
        json={"name": "Main", "account_type": "transaction", "opening_balance": "1000.00"},
    ).json()
    recurring = client.post(
        "/api/recurring-expenses",
        json={
            "name": "Merged subscription",
            "amount": "20.00",
            "frequency": "monthly",
            "next_due_date": "2026-09-01",
            "account_id": account["id"],
            "category_id": source_child["id"],
        },
    )
    assert recurring.status_code == 201

    preview = client.post(
        "/api/v018/categories/merge/preview",
        json={"source_id": source["id"], "destination_id": destination["id"]},
    )
    assert preview.status_code == 200
    assert preview.json()["source_will_be_archived"] is True
    assert preview.json()["will_reassign"]["children"] == 1

    merged = client.post(
        "/api/v018/categories/merge",
        json={"source_id": source["id"], "destination_id": destination["id"]},
    )
    assert merged.status_code == 200
    assert merged.json()["source_archived"] is True

    rows = client.get("/api/categories?include_inactive=true").json()
    source_after = next(row for row in rows if row["id"] == source["id"])
    assert source_after["is_active"] is False
    active_shared = [
        row
        for row in rows
        if row["is_active"]
        and row["parent_id"] == destination["id"]
        and normalise_category_name(row["name"]) == "shared child"
    ]
    assert len(active_shared) == 1
    canonical_child_id = active_shared[0]["id"]

    recurring_after = next(
        row
        for row in client.get("/api/recurring-expenses").json()
        if row["name"] == "Merged subscription"
    )
    assert recurring_after["category_id"] == canonical_child_id
    assert recurring_after["category"] == "Destination Parent → Shared Child"


def test_category_health_reports_historical_duplicates_without_deleting_them(client):
    setup_user(client)
    engine = get_engine()
    with engine.begin() as connection:
        now = "2026-08-20 00:00:00"
        connection.execute(
            text(
                """
                INSERT INTO categories(
                    user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at
                ) VALUES(1,'Integrity Parent',NULL,'expense','independent',1,:now,:now)
                """
            ),
            {"now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO categories(
                    user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at
                ) VALUES(1,'  integrity   parent  ',NULL,'expense','independent',1,:now,:now)
                """
            ),
            {"now": now},
        )

    health = client.get("/api/v018/categories/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "attention"
    assert any(
        group["normalised_name"] == "integrity parent"
        for group in payload["duplicate_groups"]
    )


def test_recurring_duplicate_review_is_non_destructive(client):
    setup_user(client)
    account = client.post(
        "/api/accounts",
        json={"name": "Duplicate Test", "account_type": "transaction", "opening_balance": "100.00"},
    ).json()
    for name in ("Test Subscription", "  test   subscription  "):
        response = client.post(
            "/api/recurring-expenses",
            json={
                "name": name,
                "amount": "15.00",
                "frequency": "monthly",
                "next_due_date": "2026-09-05",
                "account_id": account["id"],
            },
        )
        assert response.status_code == 201

    duplicates = client.get("/api/v018/recurring-expenses/duplicates")
    assert duplicates.status_code == 200
    payload = duplicates.json()
    assert payload["count"] >= 1
    group = next(
        item
        for item in payload["groups"]
        if any(
            normalise_category_name(row["name"]) == "test subscription"
            for row in item["records"]
        )
    )
    assert group["confidence"] == "high"
    assert len(group["records"]) == 2

    still_present = [
        row
        for row in client.get("/api/recurring-expenses").json()
        if normalise_category_name(row["name"]) == "test subscription"
    ]
    assert len(still_present) == 2


def test_commitment_dedupe_prefers_bill_linked_to_same_recurring_occurrence():
    rows = [
        {
            "kind": "recurring_expense",
            "source_id": 9,
            "recurring_expense_id": 9,
            "date": "2026-09-01",
            "name": "Internet",
            "amount": "80.00",
        },
        {
            "kind": "bill",
            "source_id": 14,
            "recurring_expense_id": 9,
            "date": "2026-09-01",
            "name": "Internet bill",
            "amount": "80.00",
        },
    ]
    deduped = dedupe_commitments(rows)
    assert len(deduped) == 1
    assert deduped[0]["kind"] == "bill"
