from sqlalchemy import text

from app.database import get_engine


def _create_account(client):
    response = client.post(
        "/api/accounts",
        json={
            "name": "Kristy ING",
            "account_type": "transaction",
            "institution": "ING",
            "opening_balance": "0.00",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_csv_import_records_transaction_span_and_unknown_coverage(client):
    account_id = _create_account(client)
    csv_text = "Date,Description,Debit,Credit\n23/07/2026,Groceries,12.50,\n15/08/2026,Wage,,100.00\n"
    response = client.post(
        "/api/imports/commit",
        json={
            "filename": "ING_Jul_Aug.csv",
            "account_id": account_id,
            "csv_text": csv_text,
            "mapping": {
                "date": "Date",
                "description": "Description",
                "debit": "Debit",
                "credit": "Credit",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_span_start"] == "2026-07-23"
    assert payload["transaction_span_end"] == "2026-08-15"
    assert payload["coverage_status"] == "unknown"

    detail = client.get(f"/api/v11/imports/{payload['batch_id']}")
    assert detail.status_code == 200
    assert detail.json()["transaction_span_start"] == "2026-07-23"
    assert detail.json()["coverage_status"] == "unknown"


def test_confirmed_coverage_is_distinct_from_transaction_span(client):
    account_id = _create_account(client)
    csv_text = "Date,Description,Amount\n23/07/2026,Groceries,-12.50\n15/08/2026,Wage,100.00\n"
    imported = client.post(
        "/api/imports/commit",
        json={
            "filename": "ING_Jul_Aug.csv",
            "account_id": account_id,
            "csv_text": csv_text,
            "mapping": {"date": "Date", "description": "Description", "amount": "Amount"},
        },
    ).json()
    response = client.put(
        f"/api/v11/imports/{imported['batch_id']}/coverage",
        json={
            "coverage_status": "confirmed",
            "coverage_start": "2026-07-23",
            "coverage_end": "2026-08-15",
        },
    )
    assert response.status_code == 200

    coverage = client.get(f"/api/v11/coverage/accounts/{account_id}?year=2026")
    assert coverage.status_code == 200
    body = coverage.json()
    assert body["confirmed_ranges"] == [{"start": "2026-07-23", "end": "2026-08-15"}]
    assert body["quality"]["status"] == "partial"


def test_overlapping_confirmed_ranges_merge_for_account_coverage(client):
    account_id = _create_account(client)
    engine = get_engine()
    with engine.begin() as connection:
        user_id = connection.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar_one()
        account = {"user_id": user_id, "account_id": account_id}
        connection.execute(
            text(
                """
                INSERT INTO import_batches (
                    user_id, filename, account_id, row_count, imported_count,
                    skipped_count, duplicate_count, matched_count, failed_count,
                    status, source_type, coverage_status, coverage_start, coverage_end,
                    transaction_span_start, transaction_span_end, created_at, updated_at
                ) VALUES
                (:user_id, 'a.csv', :account_id, 1, 1, 0, 0, 0, 0,
                 'complete', 'csv', 'confirmed', '2026-07-01', '2026-07-31',
                 '2026-07-01', '2026-07-31', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
                (:user_id, 'b.csv', :account_id, 1, 1, 0, 0, 0, 0,
                 'complete', 'csv', 'confirmed', '2026-07-23', '2026-08-15',
                 '2026-07-23', '2026-08-15', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            account,
        )
    response = client.get(f"/api/v11/coverage/accounts/{account_id}?year=2026")
    assert response.status_code == 200
    assert response.json()["confirmed_ranges"] == [{"start": "2026-07-01", "end": "2026-08-15"}]


def test_manual_transaction_does_not_create_confirmed_coverage(client):
    account_id = _create_account(client)
    created = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-08-08",
            "amount": "12.00",
            "transaction_type": "expense",
            "description": "Manual purchase",
        },
    )
    assert created.status_code == 201
    coverage = client.get(f"/api/v11/coverage/accounts/{account_id}?year=2026")
    assert coverage.status_code == 200
    assert coverage.json()["confirmed_ranges"] == []
    assert coverage.json()["quality"]["status"] == "no_data"


def test_transaction_splits_must_equal_parent_and_preserve_parent_amount(client):
    account_id = _create_account(client)
    transaction = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-08-08",
            "amount": "163.40",
            "transaction_type": "expense",
            "description": "Woolworths",
        },
    )
    assert transaction.status_code == 201
    transaction_id = transaction.json()["id"]

    invalid = client.put(
        f"/api/v11/transactions/{transaction_id}/splits",
        json={"items": [{"amount": "100.00", "category": "Groceries"}]},
    )
    assert invalid.status_code == 400

    saved = client.put(
        f"/api/v11/transactions/{transaction_id}/splits",
        json={
            "items": [
                {"amount": "121.20", "category": "Groceries"},
                {"amount": "27.20", "category": "Household"},
                {"amount": "15.00", "category": "Sienna"},
            ]
        },
    )
    assert saved.status_code == 200
    assert saved.json()["remaining"] == "0.00"
    assert len(saved.json()["items"]) == 3

    transactions = client.get(f"/api/transactions?account_id={account_id}").json()
    row = next(item for item in transactions if item["id"] == transaction_id)
    assert row["amount"] in {"-163.40", "163.40"}


def test_month_position_uses_real_month_length(client):
    july = client.get("/api/v11/coverage/month-position?value=2026-07-23")
    feb = client.get("/api/v11/coverage/month-position?value=2028-02-29")
    assert july.status_code == 200
    assert round(july.json()["percent"], 3) == round((22 / 31) * 100, 3)
    assert feb.status_code == 200
    assert round(feb.json()["percent"], 3) == round((28 / 29) * 100, 3)
