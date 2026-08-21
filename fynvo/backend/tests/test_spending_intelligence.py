from app.database import get_engine
from sqlalchemy import text


def login(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def account(client):
    return client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "0"}).json()


def add_tx(client, acc, date, amount, description, category=None, tx_type="expense"):
    payload = {"account_id": acc["id"], "date": date, "amount": amount, "transaction_type": tx_type, "description": description}
    if category:
        payload["category"] = category
    return client.post("/api/transactions", json=payload).json()


def test_intelligence_schema_rules_and_merchant_normalisation(client):
    login(client)
    acc = account(client)
    add_tx(client, acc, "2026-05-01", "50", "WOOLWORTHS 1234 MILDURA", "Groceries > Supermarket")
    add_tx(client, acc, "2026-05-08", "61", "WOOLWORTHS MILDURA VIC", "Groceries > Supermarket")

    rule = client.post("/api/intelligence/rules", json={"rule_type": "merchant", "name": "Woolworths", "match_type": "contains", "pattern": "WOOL", "normalised_merchant": "Woolworths", "priority": 10})
    assert rule.status_code == 201
    edited = client.put(f"/api/intelligence/rules/{rule.json()['id']}", json={"pattern": "WOOLWORTHS", "priority": 5})
    assert edited.status_code == 200
    preview = client.post(f"/api/intelligence/rules/{rule.json()['id']}/preview").json()
    assert preview["match_count"] == 2

    result = client.post("/api/intelligence/process")
    assert result.status_code == 200
    merchants = client.get("/api/intelligence/merchants").json()
    assert merchants[0]["merchant"] == "Woolworths"
    with get_engine().connect() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 13


def test_category_suggestions_and_dismissal_suppression(client):
    login(client)
    acc = account(client)
    for day in [1, 8, 15, 22, 29]:
        add_tx(client, acc, f"2026-06-{day:02d}", "45", "WOOLWORTHS MILDURA", "Groceries > Supermarket")
    target = add_tx(client, acc, "2026-07-06", "52", "WOOLWORTHS 9999 MILDURA")

    client.post("/api/intelligence/process")
    suggestions = client.get("/api/intelligence/suggestions").json()
    category = next(item for item in suggestions if item["suggestion_type"] == "category_suggestion" and item["action_payload"].get("transaction_id") == target["id"])
    assert category["category"] == "Groceries > Supermarket"
    assert 0 < category["confidence"] <= 1

    dismissed = client.post(f"/api/intelligence/suggestions/{category['id']}/dismiss")
    assert dismissed.status_code == 200
    remaining = client.get("/api/intelligence/suggestions").json()
    assert all(item["id"] != category["id"] for item in remaining)


def test_recurring_candidate_and_variable_spend_insight(client):
    login(client)
    acc = account(client)
    for month, amount in [(3, 120), (4, 125), (5, 121), (6, 129), (7, 123)]:
        add_tx(client, acc, f"2026-{month:02d}-15", str(amount), "TELSTRA INTERNET", "Utilities > Internet")
    client.post("/api/intelligence/process")
    suggestions = client.get("/api/intelligence/suggestions").json()
    types = {item["suggestion_type"] for item in suggestions}
    assert "recurring_candidate" in types


def test_intelligence_does_not_mutate_transaction_without_user_action(client):
    login(client)
    acc = account(client)
    tx = add_tx(client, acc, "2026-08-01", "65", "WOOLWORTHS 1234")
    before = client.get("/api/transactions").json()
    client.post("/api/intelligence/process")
    after = client.get("/api/transactions").json()
    original_before = next(row for row in before if row["id"] == tx["id"])
    original_after = next(row for row in after if row["id"] == tx["id"])
    assert original_before["category"] == original_after["category"]
