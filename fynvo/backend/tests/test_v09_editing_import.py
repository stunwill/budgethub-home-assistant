from app.database import get_engine
from sqlalchemy import text


def login(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})


def create_account(client, name="Everyday"):
    res = client.post("/api/accounts", json={"name": name, "account_type": "transaction", "opening_balance": "1000.00"})
    assert res.status_code == 201
    return res.json()


def test_all_major_records_can_be_edited_and_persist(client):
    login(client)
    account = create_account(client)

    tx = client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-20", "amount": "-50.00", "transaction_type": "expense", "description": "Original shop", "category": "Groceries"}).json()
    assert client.put(f"/api/transactions/{tx['id']}", json={"description": "Updated shop", "amount": "-61.25", "category": "Groceries > Supermarket"}).status_code == 200
    assert any(row["description"] == "Updated shop" and row["amount"] == "-61.25" for row in client.get("/api/transactions").json())

    assert client.put(f"/api/accounts/{account['id']}", json={"name": "ING Everyday", "institution": "ING"}).status_code == 200
    assert any(row["name"] == "ING Everyday" for row in client.get("/api/accounts").json())

    income = client.post("/api/income", json={"name": "Salary", "amount": "2500", "frequency": "fortnightly", "next_payment_date": "2026-08-28", "destination_account_id": account["id"]}).json()
    assert client.put(f"/api/income/{income['id']}", json={"amount": "2750", "effective_from": "2026-11-12", "payer": "Employer"}).status_code == 200
    assert any(row["amount"] == "2750.00" and row["payer"] == "Employer" for row in client.get("/api/income").json())

    recurring = client.post("/api/recurring-expenses", json={"name": "Internet", "amount": "140", "frequency": "monthly", "next_due_date": "2026-09-01", "account_id": account["id"], "category": "Utilities > Internet"}).json()
    assert client.put(f"/api/recurring-expenses/{recurring['id']}", json={"amount": "80", "effective_from": "2026-10-01", "notes": "Plan changed"}).status_code == 200
    recurring_after = next(row for row in client.get("/api/recurring-expenses").json() if row["id"] == recurring["id"])
    assert recurring_after["amount"] == "140.00"
    assert recurring_after["notes"] == "Plan changed"
    with get_engine().connect() as connection:
        future_change = connection.execute(
            text("SELECT new_amount_cents, effective_from FROM effective_amount_changes WHERE record_type='recurring_expense' AND record_id=:id ORDER BY id DESC LIMIT 1"),
            {"id": recurring["id"]},
        ).first()
    assert future_change is not None
    assert future_change.new_amount_cents == 8000
    assert str(future_change.effective_from)[:10] == "2026-10-01"

    bill = client.post("/api/bills", json={"name": "Electricity", "provider": "Powershop", "amount": "280", "due_date": "2026-08-22", "bill_type": "Utilities > Electricity"}).json()
    assert client.put(f"/api/bills/{bill['id']}", json={"amount": "296.40", "due_date": "2026-08-23", "status": "paid"}).status_code == 200
    edited_bill = next(row for row in client.get("/api/bills").json() if row["id"] == bill["id"])
    assert edited_bill["amount"] == "0.00"
    assert edited_bill["status"] == "paid"

    planned = client.post("/api/planned-spending", json={"name": "Tyres", "estimated_amount": "1200", "planned_date": "2026-09-01", "category": "Transport > Car"}).json()
    assert client.put(f"/api/planned-spending/{planned['id']}", json={"estimated_amount": "1168", "merchant": "Bob Jane", "status": "committed"}).status_code == 200
    assert any(row["estimated_amount"] == "1168.00" and row["merchant"] == "Bob Jane" for row in client.get("/api/planned-spending").json())

    parent = client.post("/api/categories", json={"name": "Custom Utilities", "budget_relationship": "shared_parent_pool"}).json()
    child = client.post("/api/categories", json={"name": "Custom Electricity", "parent_id": parent["id"]}).json()
    assert client.put(f"/api/categories/{child['id']}", json={"name": "Power", "parent_id": parent["id"], "color": "#1f6feb"}).status_code == 200
    assert any(row["path"] == "Custom Utilities → Power" for row in client.get("/api/categories").json())

    budget = client.post("/api/budgets", json={"name": "Custom Utilities", "category_id": parent["id"], "category_name": "Custom Utilities", "amount": "600", "period": "monthly", "start_date": "2026-08-01", "anchor_date": "2026-08-01"}).json()
    assert client.put(f"/api/budgets/{budget['id']}", json={"amount": "650", "effective_from": "2026-09-01", "relationship_mode": "shared_parent_pool"}).status_code == 200
    assert any(row["amount"] == "650.00" and row["relationship_mode"] == "shared_parent_pool" for row in client.get("/api/budgets").json())

    with get_engine().connect() as connection:
        edits = connection.execute(text("SELECT COUNT(*) FROM edit_history")).scalar()
        changes = connection.execute(text("SELECT COUNT(*) FROM effective_amount_changes")).scalar()
    assert edits >= 3
    assert changes >= 2


def test_csv_preview_import_duplicate_and_reconciliation(client):
    login(client)
    account = create_account(client)
    bill = client.post("/api/bills", json={"name": "Electricity", "provider": "Powershop", "amount": "280", "due_date": "2026-08-22", "bill_type": "Utilities > Electricity"}).json()
    client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-20", "amount": "50", "transaction_type": "income", "description": "WOOLWORTHS MILDURA", "category": "Groceries"})
    csv_text = "Date,Description,Debit,Credit\n20/08/2026,WOOLWORTHS 1234 MILDURA,,50.00\n22/08/2026,POWERSHOP,278.64,\n23/08/26,TELSTRA,120.00,\n"
    payload = {"filename": "ing.csv", "account_id": account["id"], "csv_text": csv_text, "mapping": {"date": "Date", "description": "Description", "debit": "Debit", "credit": "Credit"}}
    preview = client.post("/api/imports/preview", json=payload)
    assert preview.status_code == 200
    rows = preview.json()["rows"]
    assert any("duplicate" in row["status"] for row in rows)
    assert any(row["matches"] for row in rows)

    result = client.post("/api/imports/commit", json=payload)
    assert result.status_code == 200
    body = result.json()
    assert body["new_transactions"] >= 2
    assert body["duplicates_skipped"] >= 1
    assert body["matched"] >= 1

    history = client.get("/api/imports/history").json()
    assert history[0]["filename"] == "ing.csv"
    review = client.get("/api/reconciliation/review-queue").json()
    assert review
    accepted = client.post(f"/api/reconciliation/{review[0]['id']}/accept")
    assert accepted.status_code == 200
    bills = client.get("/api/bills").json()
    if review[0]["source_type"] == "bill" and review[0]["source_id"] == bill["id"]:
        assert next(row for row in bills if row["id"] == bill["id"])["status"] == "paid"

    analysis = client.get("/api/budgets/analysis").json()
    assert "summary" in analysis
