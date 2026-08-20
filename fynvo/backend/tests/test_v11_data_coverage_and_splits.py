from app.database import get_engine
from app.v11 import _totp
from sqlalchemy import text


def _create_account(client, name="Kristy ING"):
    response = client.post(
        "/api/accounts",
        json={
            "name": name,
            "account_type": "transaction",
            "institution": "ING",
            "opening_balance": "0.00",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _import(client, account_id, filename="ING_Jul_Aug.csv"):
    csv_text = "Date,Description,Debit,Credit\n23/07/2026,Groceries,12.50,\n15/08/2026,Wage,,100.00\n"
    return client.post(
        "/api/imports/commit",
        json={
            "filename": filename,
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


def test_csv_import_requires_account(client):
    response = client.post(
        "/api/imports/commit",
        json={"filename": "missing-account.csv", "csv_text": "Date,Amount\n01/01/2026,1.00\n"},
    )
    assert response.status_code == 400
    assert "Account" in response.json()["detail"]


def test_csv_import_records_transaction_span_and_unknown_coverage(client):
    account_id = _create_account(client)
    response = _import(client, account_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_span_start"] == "2026-07-23"
    assert payload["transaction_span_end"] == "2026-08-15"
    assert payload["coverage_status"] == "unknown"

    detail = client.get(f"/api/v11/imports/{payload['batch_id']}")
    assert detail.status_code == 200
    assert detail.json()["transaction_span_start"] == "2026-07-23"
    assert detail.json()["coverage_status"] == "unknown"
    assert detail.json()["raw_file_retained"] is False


def test_zero_success_rows_do_not_fabricate_transaction_span(client):
    account_id = _create_account(client)
    response = client.post(
        "/api/imports/commit",
        json={
            "filename": "invalid.csv",
            "account_id": account_id,
            "csv_text": "Date,Description,Amount\nnot-a-date,Broken,not-money\n",
            "mapping": {"date": "Date", "description": "Description", "amount": "Amount"},
        },
    )
    assert response.status_code == 200
    assert response.json()["new_transactions"] == 0
    assert response.json()["transaction_span_start"] is None
    assert response.json()["transaction_span_end"] is None


def test_duplicate_import_does_not_duplicate_actual_or_extend_coverage(client):
    account_id = _create_account(client)
    first = _import(client, account_id, "first.csv")
    second = _import(client, account_id, "second.csv")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["new_transactions"] == 2
    assert second.json()["new_transactions"] == 0
    assert second.json()["duplicates_skipped"] == 2
    assert second.json()["transaction_span_start"] is None
    transactions = client.get(f"/api/transactions?account_id={account_id}").json()
    imported = [row for row in transactions if row.get("source") == "csv"]
    assert len(imported) == 2


def test_confirmed_coverage_is_distinct_from_transaction_span(client):
    account_id = _create_account(client)
    imported = _import(client, account_id).json()
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


def test_known_coverage_gap_is_structured_and_visible(client):
    account_id = _create_account(client)
    gap = client.post(
        f"/api/v11/coverage/accounts/{account_id}/gaps",
        json={"start_date": "2026-05-01", "end_date": "2026-05-14", "reason": "Statement missing"},
    )
    assert gap.status_code == 201
    coverage = client.get(f"/api/v11/coverage/accounts/{account_id}?year=2026")
    assert coverage.status_code == 200
    assert coverage.json()["known_gaps"][0]["start"] == "2026-05-01"
    assert coverage.json()["known_gaps"][0]["reason"] == "Statement missing"


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


def test_contiguous_confirmed_ranges_merge(client):
    account_id = _create_account(client)
    engine = get_engine()
    with engine.begin() as connection:
        user_id = connection.execute(text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar_one()
        for filename, start, end in (
            ("a.csv", "2026-01-01", "2026-03-31"),
            ("b.csv", "2026-04-01", "2026-06-30"),
        ):
            connection.execute(text("""
                INSERT INTO import_batches (
                    user_id, filename, account_id, row_count, imported_count, skipped_count,
                    duplicate_count, matched_count, failed_count, status, source_type,
                    coverage_status, coverage_start, coverage_end, transaction_span_start,
                    transaction_span_end, created_at, updated_at
                ) VALUES (
                    :uid, :filename, :account_id, 1, 1, 0, 0, 0, 0, 'complete', 'csv',
                    'confirmed', :start, :end, :start, :end, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
            """), {"uid": user_id, "filename": filename, "account_id": account_id, "start": start, "end": end})
    response = client.get(f"/api/v11/coverage/accounts/{account_id}?year=2026")
    assert response.json()["confirmed_ranges"] == [{"start": "2026-01-01", "end": "2026-06-30"}]


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


def test_split_edit_keeps_stable_allocation_identity(client):
    account_id = _create_account(client)
    transaction_id = client.post(
        "/api/transactions",
        json={"account_id": account_id, "date": "2026-08-08", "amount": "10.00", "transaction_type": "expense", "description": "Mixed"},
    ).json()["id"]
    first = client.put(
        f"/api/v11/transactions/{transaction_id}/splits",
        json={"items": [{"amount": "6.00", "category": "A"}, {"amount": "4.00", "category": "B"}]},
    ).json()
    first_id = first["items"][0]["id"]
    second = client.put(
        f"/api/v11/transactions/{transaction_id}/splits",
        json={"items": [{"id": first_id, "amount": "7.00", "category": "A"}, {"amount": "3.00", "category": "C"}]},
    )
    assert second.status_code == 200
    assert any(item["id"] == first_id and item["amount"] == "7.00" for item in second.json()["items"])


def test_month_position_uses_real_month_length(client):
    july = client.get("/api/v11/coverage/month-position?value=2026-07-23")
    feb = client.get("/api/v11/coverage/month-position?value=2028-02-29")
    assert july.status_code == 200
    assert round(july.json()["percent"], 3) == round((22 / 31) * 100, 3)
    assert feb.status_code == 200
    assert round(feb.json()["percent"], 3) == round((28 / 29) * 100, 3)


def test_mfa_enrolment_does_not_enable_until_verified(client):
    enrol = client.post("/api/v11/mfa/enrol")
    assert enrol.status_code == 200
    secret = enrol.json()["secret"]
    before = client.get("/api/v11/mfa/state")
    assert before.json()["enabled"] is False
    assert "secret" not in before.json()

    activated = client.post("/api/v11/mfa/activate", json={"code": _totp(secret)})
    assert activated.status_code == 200
    assert activated.json()["enabled"] is True
    assert len(activated.json()["recovery_codes"]) == 10
    after = client.get("/api/v11/mfa/state")
    assert after.json()["enabled"] is True
    assert "secret" not in after.json()


def test_structured_export_preserves_v11_relationship_datasets(client):
    account_id = _create_account(client)
    _import(client, account_id)
    response = client.get("/api/v11/exports/full")
    assert response.status_code == 200
    body = response.json()
    assert body["format"] == "fynvo-json-v1.1"
    assert "transactions" in body
    assert "transaction_splits" in body
    assert "import_batches" in body
    assert "coverage_gaps" in body
    assert "transaction_import_provenance" in body["relationships"]

    csv_response = client.get("/api/v11/exports/transactions.csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert csv_response.headers["cache-control"] == "no-store"
