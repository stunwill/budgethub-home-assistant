from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import secrets
import struct
import time
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session as DbSession

from . import auth as auth_module
from . import budget as budget_module
from . import database as database_module
from . import v09 as legacy_v09
from .auth import SESSION_COOKIE, get_client_key, get_current_user, start_session
from .config import get_settings
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import hash_token, new_session_token, utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)
SESSION = SESSION_COOKIE
COVERAGE_STATUSES = {"unknown", "partial", "confirmed"}
CURRENT_COVERAGE_THRESHOLD_DAYS = 3
MFA_CHALLENGE_MINUTES = 5
MFA_ISSUER = "Fynvo"


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date") from exc


def _as_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _month_day_percent(day: date) -> float:
    if day.month == 12:
        next_month = date(day.year + 1, 1, 1)
    else:
        next_month = date(day.year, day.month + 1, 1)
    days_in_month = (next_month - date(day.year, day.month, 1)).days
    return ((day.day - 1) / days_in_month) * 100


def _merge_intervals(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[list[date]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1] + timedelta(days=1):
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(start, end) for start, end in merged]


def _gaps_between(intervals: list[tuple[date, date]]) -> list[tuple[date, date]]:
    merged = _merge_intervals(intervals)
    return [
        (left[1] + timedelta(days=1), right[0] - timedelta(days=1))
        for left, right in zip(merged, merged[1:], strict=False)
        if right[0] > left[1] + timedelta(days=1)
    ]


def _ranges_overlap(left: tuple[date, date], right: tuple[date, date]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _coverage_quality(
    confirmed: list[tuple[date, date]],
    selected_start: date,
    selected_end: date,
    uncertain: list[tuple[date, date]] | None = None,
    known_gaps: list[tuple[date, date]] | None = None,
) -> dict[str, Any]:
    uncertain = uncertain or []
    known_gaps = known_gaps or []
    if not confirmed:
        return {
            "status": "no_data",
            "reason": "No confirmed imported or synchronised Actual source coverage exists.",
            "gaps": [],
        }

    today = utcnow().date()
    analysis_end = min(selected_end, today) if selected_start.year == today.year else selected_end
    merged = _merge_intervals(confirmed)
    missing: list[tuple[date, date]] = []
    cursor = selected_start
    for start, end in merged:
        if end < selected_start or start > analysis_end:
            continue
        bounded_start = max(start, selected_start)
        bounded_end = min(end, analysis_end)
        if bounded_start > cursor:
            missing.append((cursor, bounded_start - timedelta(days=1)))
        cursor = max(cursor, bounded_end + timedelta(days=1))
    if cursor <= analysis_end:
        missing.append((cursor, analysis_end))

    explicit_gaps = [
        (max(start, selected_start), min(end, analysis_end))
        for start, end in known_gaps
        if _ranges_overlap((start, end), (selected_start, analysis_end))
    ]
    uncertain_visible = [
        (max(start, selected_start), min(end, analysis_end))
        for start, end in uncertain
        if _ranges_overlap((start, end), (selected_start, analysis_end))
    ]
    all_gaps = _merge_intervals(missing + explicit_gaps)
    gap_payload = [{"start": start.isoformat(), "end": end.isoformat()} for start, end in all_gaps]

    if explicit_gaps:
        start, end = explicit_gaps[0]
        return {
            "status": "partial",
            "reason": f"Known source-data gap from {start.isoformat()} to {end.isoformat()}.",
            "gaps": gap_payload,
        }
    if all_gaps:
        start, end = all_gaps[0]
        return {
            "status": "partial",
            "reason": f"Actual source coverage is incomplete; first uncovered period is {start.isoformat()} to {end.isoformat()}.",
            "gaps": gap_payload,
        }
    if uncertain_visible:
        return {
            "status": "partial",
            "reason": "The selected period includes source data whose completeness is uncertain.",
            "gaps": [],
        }

    latest_end = max(end for _, end in merged)
    if selected_start.year == today.year and latest_end >= today - timedelta(days=CURRENT_COVERAGE_THRESHOLD_DAYS):
        return {
            "status": "current",
            "reason": (
                "Confirmed source coverage is continuous and extends to within "
                f"{CURRENT_COVERAGE_THRESHOLD_DAYS} calendar days of today."
            ),
            "gaps": [],
        }
    return {
        "status": "continuous",
        "reason": "Confirmed source coverage is continuous across the selected analysis period.",
        "gaps": [],
    }


def _table_exists(db: DbSession, table_name: str) -> bool:
    return table_name in inspect(db.get_bind()).get_table_names()


def _run_v11_complete_migrations() -> None:
    engine = database_module.get_engine()
    with engine.begin() as connection:
        columns = {row["name"] for row in connection.execute(text("PRAGMA table_info(import_batches)")).mappings()}
        if "archived_at" not in columns:
            connection.execute(text("ALTER TABLE import_batches ADD COLUMN archived_at DATETIME"))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS import_row_diagnostics (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                import_batch_id INTEGER NOT NULL,
                row_number INTEGER,
                diagnostic_type VARCHAR(40) NOT NULL,
                message VARCHAR(500) NOT NULL,
                transaction_date DATE,
                amount_cents INTEGER,
                description VARCHAR(180),
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(import_batch_id) REFERENCES import_batches(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS known_coverage_gaps (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                reason VARCHAR(500),
                source_batch_id INTEGER,
                created_by INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id),
                FOREIGN KEY(source_batch_id) REFERENCES import_batches(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS mfa_settings (
                user_id INTEGER PRIMARY KEY,
                enabled BOOLEAN NOT NULL DEFAULT 0,
                secret TEXT,
                pending_secret TEXT,
                enabled_at DATETIME,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS mfa_recovery_codes (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                code_hash VARCHAR(128) NOT NULL,
                used_at DATETIME,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS mfa_login_challenges (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                token_hash VARCHAR(128) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS data_exports (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                export_format VARCHAR(20) NOT NULL,
                dataset VARCHAR(80) NOT NULL,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_import_row_diagnostics_batch "
            "ON import_row_diagnostics(user_id, import_batch_id, row_number)"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_known_coverage_gaps_account "
            "ON known_coverage_gaps(user_id, account_id, start_date, end_date)"
        ))
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_mfa_login_challenges_token "
            "ON mfa_login_challenges(token_hash, expires_at)"
        ))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (11)"))
        elif int(current) < 11:
            connection.execute(text("UPDATE schema_version SET version=11"))


if not getattr(database_module.run_migrations, "_fynvo_v11_complete", False):
    _previous_run_migrations = database_module.run_migrations

    def _run_migrations_complete() -> None:
        _previous_run_migrations()
        _run_v11_complete_migrations()

    _run_migrations_complete._fynvo_v11_complete = True  # type: ignore[attr-defined]
    database_module.run_migrations = _run_migrations_complete


# v0.9 owns the established CSV endpoint. Replace only its commit route so the
# existing preview and parsing flow is preserved while v1.1 records diagnostics
# and source-neutral provenance.
legacy_v09.router.routes = [
    route
    for route in legacy_v09.router.routes
    if not (
        getattr(route, "path", None) == "/api/imports/commit"
        and "POST" in getattr(route, "methods", set())
    )
]


def _account_for_import(db: DbSession, user: User, account_id: int) -> dict[str, Any]:
    row = db.execute(
        text("SELECT id, name, institution FROM accounts WHERE id=:id AND user_id=:uid AND is_active=1"),
        {"id": account_id, "uid": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=400, detail="Choose a valid destination Account")
    return dict(row)


def _diagnostic_type(errors: list[str]) -> str:
    message = " ".join(errors).lower()
    if "date" in message:
        return "invalid_date"
    if "amount" in message:
        return "invalid_amount"
    if "missing" in message:
        return "missing_required_field"
    return "malformed_row"


def _record_import_diagnostic(
    db: DbSession,
    user: User,
    batch_id: int,
    row: dict[str, Any],
    diagnostic_type: str,
    message: str,
    now: datetime,
) -> None:
    tx_date = _as_date(row.get("date")) if row.get("date") else None
    amount_cents = row.get("amount_cents")
    db.execute(text("""
        INSERT INTO import_row_diagnostics (
            user_id, import_batch_id, row_number, diagnostic_type, message,
            transaction_date, amount_cents, description, created_at
        ) VALUES (
            :uid, :batch, :row_number, :kind, :message,
            :tx_date, :amount, :description, :now
        )
    """), {
        "uid": user.id,
        "batch": batch_id,
        "row_number": row.get("row_number"),
        "kind": diagnostic_type,
        "message": message[:500],
        "tx_date": tx_date,
        "amount": amount_cents,
        "description": str(row.get("description") or "")[:180] or None,
        "now": now,
    })


def _already_imported(db: DbSession, user: User, account_id: int, row: dict[str, Any]) -> bool:
    fingerprint = row.get("fingerprint")
    if fingerprint:
        found = db.execute(text("""
            SELECT id FROM transactions
            WHERE user_id=:uid AND account_id=:account_id AND external_id=:external_id
            LIMIT 1
        """), {
            "uid": user.id,
            "account_id": account_id,
            "external_id": fingerprint,
        }).scalar()
        if found:
            return True
    return "duplicate" in str(row.get("status") or "")


@router.post("/imports/commit")
def import_commit_v11(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    account_id = int(payload.get("account_id") or 0)
    if not account_id:
        raise HTTPException(status_code=400, detail="Destination Account is required")
    account = _account_for_import(db, current_user, account_id)
    rows = legacy_v09._preview_rows(
        db,
        current_user,
        payload.get("csv_text") or "",
        payload.get("mapping") or {},
        account_id,
    )
    now = utcnow()
    filename = legacy_v09.re.sub(
        r"[^A-Za-z0-9_. -]",
        "_",
        payload.get("filename") or "bank-import.csv",
    )[:180]
    source_type = str(payload.get("source_type") or "csv_import")[:40]
    source_institution = (
        str(payload.get("source_institution") or account.get("institution") or "")[:140] or None
    )
    parser_profile = str(payload.get("source_name") or "Australian bank CSV")[:180]
    db.execute(text("""
        INSERT INTO import_batches (
            user_id, filename, account_id, row_count, imported_count, skipped_count,
            duplicate_count, matched_count, failed_count, status, source_type,
            source_institution, parser_profile, coverage_status, created_at, updated_at
        ) VALUES (
            :uid, :filename, :account_id, :row_count, 0, 0, 0, 0, 0,
            'processing', :source_type, :institution, :parser_profile,
            'unknown', :now, :now
        )
    """), {
        "uid": current_user.id,
        "filename": filename,
        "account_id": account_id,
        "row_count": len(rows),
        "source_type": source_type,
        "institution": source_institution,
        "parser_profile": parser_profile,
        "now": now,
    })
    batch_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    imported = skipped = duplicates = matched = failed = 0
    imported_rows: list[dict[str, Any]] = []
    accepted_dates: list[date] = []

    for row in rows:
        if row.get("errors"):
            failed += 1
            errors = [str(item) for item in row["errors"]]
            _record_import_diagnostic(
                db,
                current_user,
                batch_id,
                row,
                _diagnostic_type(errors),
                "; ".join(errors),
                now,
            )
            continue
        if _already_imported(db, current_user, account_id, row):
            duplicates += 1
            skipped += 1
            _record_import_diagnostic(
                db,
                current_user,
                batch_id,
                row,
                "duplicate_transaction",
                "Transaction already exists and was skipped.",
                now,
            )
            continue

        tx_date = _as_date(row.get("date"))
        if tx_date is None:
            failed += 1
            _record_import_diagnostic(
                db,
                current_user,
                batch_id,
                row,
                "invalid_date",
                "Accepted transaction date could not be established.",
                now,
            )
            continue
        signed_amount = (
            row["amount"]
            if row["transaction_type"] == "income"
            else f"-{row['amount']}"
        )
        created = legacy_v09.create_transaction(
            db,
            current_user,
            legacy_v09.TransactionCreate(
                account_id=account_id,
                date=tx_date,
                amount=signed_amount,
                transaction_type=row["transaction_type"],
                description=row["description"],
                merchant=row["merchant"],
                category=row["category"],
                source="csv",
                status="cleared",
                raw_description=row["description"],
            ),
        )
        db.execute(text("""
            UPDATE transactions
            SET import_batch_id=:batch_id, external_id=:external_id,
                import_date=:now, reconciliation_state=:state
            WHERE id=:id AND user_id=:uid
        """), {
            "batch_id": str(batch_id),
            "external_id": row.get("fingerprint"),
            "now": now,
            "state": "suggested_match" if row.get("matches") else "unmatched",
            "id": created["id"],
            "uid": current_user.id,
        })
        if row.get("matches"):
            best = row["matches"][0]
            db.execute(text("""
                INSERT INTO reconciliation_links (
                    user_id, transaction_id, source_type, source_id,
                    expected_amount_cents, actual_amount_cents, variance_cents,
                    status, confidence, created_at, updated_at
                ) VALUES (
                    :uid, :transaction_id, :source_type, :source_id,
                    :expected, :actual, :variance,
                    'suggested_match', :confidence, :now, :now
                )
            """), {
                "uid": current_user.id,
                "transaction_id": created["id"],
                "source_type": best["source_type"],
                "source_id": best["source_id"],
                "expected": parse_money(best["expected_amount"]),
                "actual": row["amount_cents"],
                "variance": parse_money(best["variance"]),
                "confidence": best["confidence"],
                "now": now,
            })
            matched += 1
        imported += 1
        accepted_dates.append(tx_date)
        imported_rows.append(created)

    span_start = min(accepted_dates) if accepted_dates else None
    span_end = max(accepted_dates) if accepted_dates else None
    db.execute(text("""
        UPDATE import_batches
        SET imported_count=:imported, skipped_count=:skipped,
            duplicate_count=:duplicates, matched_count=:matched,
            failed_count=:failed, status='complete',
            transaction_span_start=:span_start,
            transaction_span_end=:span_end,
            updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {
        "id": batch_id,
        "uid": current_user.id,
        "imported": imported,
        "skipped": skipped,
        "duplicates": duplicates,
        "matched": matched,
        "failed": failed,
        "span_start": span_start,
        "span_end": span_end,
        "now": now,
    })
    db.commit()
    return {
        "batch_id": batch_id,
        "rows_processed": len(rows),
        "new_transactions": imported,
        "duplicates_skipped": duplicates,
        "matched": matched,
        "failed": failed,
        "transaction_span_start": span_start.isoformat() if span_start else None,
        "transaction_span_end": span_end.isoformat() if span_end else None,
        "coverage_status": "unknown",
        "transactions": imported_rows,
    }


def _breakdown(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        label = str(row.get(key) or "Uncategorised")
        item = grouped.setdefault(label, {"count": 0, "amount_cents": 0})
        item["count"] += 1
        item["amount_cents"] += abs(int(row.get("amount_cents") or 0))
    return [
        {
            "name": name,
            "count": values["count"],
            "amount": cents_to_decimal(values["amount_cents"]),
        }
        for name, values in sorted(
            grouped.items(),
            key=lambda item: item[1]["amount_cents"],
            reverse=True,
        )
    ]


@router.get("/v11/imports/{batch_id}")
def import_detail(batch_id: int, current_user: User = USER, db: DbSession = DB):
    batch = db.execute(text("""
        SELECT ib.*, a.name AS account_name
        FROM import_batches ib
        JOIN accounts a ON a.id=ib.account_id AND a.user_id=ib.user_id
        WHERE ib.id=:id AND ib.user_id=:uid
    """), {"id": batch_id, "uid": current_user.id}).mappings().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    transaction_rows = [
        dict(row)
        for row in db.execute(text("""
            SELECT id, account_id, transaction_date, amount_cents, transaction_type,
                   description, merchant, category, status, reconciliation_state,
                   external_id, import_date
            FROM transactions
            WHERE user_id=:uid AND import_batch_id=:batch
            ORDER BY transaction_date, id
        """), {"uid": current_user.id, "batch": str(batch_id)}).mappings().all()
    ]
    diagnostics = [
        dict(row)
        for row in db.execute(text("""
            SELECT id, row_number, diagnostic_type, message, transaction_date,
                   amount_cents, description, created_at
            FROM import_row_diagnostics
            WHERE user_id=:uid AND import_batch_id=:batch
            ORDER BY row_number, id
        """), {"uid": current_user.id, "batch": batch_id}).mappings().all()
    ] if _table_exists(db, "import_row_diagnostics") else []
    credit_cents = sum(
        abs(row["amount_cents"])
        for row in transaction_rows
        if row["transaction_type"] == "income" or row["amount_cents"] > 0
    )
    debit_cents = sum(
        abs(row["amount_cents"])
        for row in transaction_rows
        if not (row["transaction_type"] == "income" or row["amount_cents"] > 0)
    )
    return {
        "id": batch["id"],
        "filename": batch["filename"],
        "account_id": batch["account_id"],
        "account_name": batch["account_name"],
        "source_type": batch.get("source_type") or "csv_import",
        "source_institution": batch.get("source_institution"),
        "parser_profile": batch.get("parser_profile"),
        "created_at": str(batch["created_at"]),
        "status": batch["status"],
        "archived_at": str(batch.get("archived_at")) if batch.get("archived_at") else None,
        "row_count": batch["row_count"],
        "imported_count": batch["imported_count"],
        "skipped_count": batch["skipped_count"],
        "duplicate_count": batch["duplicate_count"],
        "matched_count": batch["matched_count"],
        "failed_count": batch["failed_count"],
        "transaction_span_start": str(batch.get("transaction_span_start")) if batch.get("transaction_span_start") else None,
        "transaction_span_end": str(batch.get("transaction_span_end")) if batch.get("transaction_span_end") else None,
        "coverage_status": batch.get("coverage_status") or "unknown",
        "coverage_start": str(batch.get("coverage_start")) if batch.get("coverage_start") else None,
        "coverage_end": str(batch.get("coverage_end")) if batch.get("coverage_end") else None,
        "coverage_note": batch.get("coverage_note"),
        "totals": {
            "credits": cents_to_decimal(credit_cents),
            "debits": cents_to_decimal(debit_cents),
            "net_movement": cents_to_decimal(credit_cents - debit_cents),
        },
        "category_breakdown": _breakdown(transaction_rows, "category"),
        "merchant_breakdown": _breakdown(transaction_rows, "merchant"),
        "rejected_rows": diagnostics,
        "transactions": [
            {**row, "amount": cents_to_decimal(row["amount_cents"])}
            for row in transaction_rows
        ],
        "raw_file_retained": False,
    }


@router.post("/v11/imports/{batch_id}/archive")
def archive_import(batch_id: int, current_user: User = USER, db: DbSession = DB):
    result = db.execute(text("""
        UPDATE import_batches
        SET archived_at=:now, updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"now": utcnow(), "id": batch_id, "uid": current_user.id})
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Import batch not found")
    db.commit()
    return {
        "status": "archived",
        "batch_id": batch_id,
        "transactions_preserved": True,
        "coverage_preserved": True,
    }


@router.get("/v11/imports/{batch_id}/reverse-preview")
def import_reverse_preview(batch_id: int, current_user: User = USER, db: DbSession = DB):
    batch = db.execute(
        text("SELECT id FROM import_batches WHERE id=:id AND user_id=:uid"),
        {"id": batch_id, "uid": current_user.id},
    ).scalar()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    transaction_count = int(db.execute(text("""
        SELECT COUNT(*) FROM transactions
        WHERE user_id=:uid AND import_batch_id=:batch
    """), {"uid": current_user.id, "batch": str(batch_id)}).scalar() or 0)
    split_count = int(db.execute(text("""
        SELECT COUNT(*) FROM transaction_splits s
        JOIN transactions t ON t.id=s.transaction_id AND t.user_id=s.user_id
        WHERE t.user_id=:uid AND t.import_batch_id=:batch
    """), {"uid": current_user.id, "batch": str(batch_id)}).scalar() or 0)
    reconciliation_count = int(db.execute(text("""
        SELECT COUNT(*) FROM reconciliation_links r
        JOIN transactions t ON t.id=r.transaction_id AND t.user_id=r.user_id
        WHERE t.user_id=:uid AND t.import_batch_id=:batch
    """), {"uid": current_user.id, "batch": str(batch_id)}).scalar() or 0)
    return {
        "batch_id": batch_id,
        "affected_transactions": transaction_count,
        "split_allocations": split_count,
        "reconciliation_links": reconciliation_count,
        "reversal_supported": False,
        "reason": (
            "v1.1 preserves financial history. Archive the import record instead; "
            "transaction reversal is deferred until relationship-safe reversal is implemented."
        ),
    }


@router.put("/v11/imports/{batch_id}/coverage")
def set_import_coverage(
    batch_id: int,
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
):
    batch = db.execute(
        text("SELECT * FROM import_batches WHERE id=:id AND user_id=:uid"),
        {"id": batch_id, "uid": current_user.id},
    ).mappings().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    coverage_status = str(payload.get("coverage_status") or "unknown").lower()
    if coverage_status not in COVERAGE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid coverage status")
    start = _as_date(payload.get("coverage_start"))
    end = _as_date(payload.get("coverage_end"))
    if coverage_status == "confirmed":
        start = start or _as_date(batch.get("transaction_span_start"))
        end = end or _as_date(batch.get("transaction_span_end"))
        if not start or not end:
            raise HTTPException(
                status_code=400,
                detail="Confirmed coverage requires a start and end date",
            )
    if coverage_status == "unknown":
        start = None
        end = None
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="Coverage end must be on or after coverage start")
    now = utcnow()
    db.execute(text("""
        UPDATE import_batches
        SET coverage_status=:coverage_status, coverage_start=:start,
            coverage_end=:end, coverage_note=:note,
            coverage_confirmed_at=:confirmed_at,
            coverage_confirmed_by=:confirmed_by, updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {
        "coverage_status": coverage_status,
        "start": start,
        "end": end,
        "note": str(payload.get("coverage_note") or "")[:500] or None,
        "confirmed_at": now if coverage_status == "confirmed" else None,
        "confirmed_by": current_user.id if coverage_status == "confirmed" else None,
        "now": now,
        "id": batch_id,
        "uid": current_user.id,
    })
    db.commit()
    return {
        "status": "ok",
        "batch_id": batch_id,
        "coverage_status": coverage_status,
        "coverage_start": start.isoformat() if start else None,
        "coverage_end": end.isoformat() if end else None,
    }


def _account_exists(db: DbSession, user: User, account_id: int) -> bool:
    return bool(db.execute(
        text("SELECT id FROM accounts WHERE id=:id AND user_id=:uid"),
        {"id": account_id, "uid": user.id},
    ).scalar())


@router.post("/v11/coverage/accounts/{account_id}/gaps", status_code=status.HTTP_201_CREATED)
def create_known_gap(
    account_id: int,
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
):
    if not _account_exists(db, current_user, account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    start = _as_date(payload.get("start_date"))
    end = _as_date(payload.get("end_date"))
    if not start or not end:
        raise HTTPException(status_code=400, detail="Gap start and end dates are required")
    if end < start:
        raise HTTPException(status_code=400, detail="Gap end must be on or after its start")
    source_batch_id = payload.get("source_batch_id")
    now = utcnow()
    db.execute(text("""
        INSERT INTO known_coverage_gaps (
            user_id, account_id, start_date, end_date, reason,
            source_batch_id, created_by, created_at, updated_at
        ) VALUES (
            :uid, :account_id, :start_date, :end_date, :reason,
            :source_batch_id, :created_by, :now, :now
        )
    """), {
        "uid": current_user.id,
        "account_id": account_id,
        "start_date": start,
        "end_date": end,
        "reason": str(payload.get("reason") or "Known source-data gap")[:500],
        "source_batch_id": int(source_batch_id) if source_batch_id else None,
        "created_by": current_user.id,
        "now": now,
    })
    gap_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.commit()
    return {"id": gap_id, "start": start.isoformat(), "end": end.isoformat()}


@router.delete("/v11/coverage/gaps/{gap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_known_gap(gap_id: int, current_user: User = USER, db: DbSession = DB):
    db.execute(
        text("DELETE FROM known_coverage_gaps WHERE id=:id AND user_id=:uid"),
        {"id": gap_id, "uid": current_user.id},
    )
    db.commit()


@router.get("/v11/coverage/accounts/{account_id}")
def account_coverage(
    account_id: int,
    year: int | None = Query(None, ge=2000, le=2200),
    current_user: User = USER,
    db: DbSession = DB,
):
    account = db.execute(text("""
        SELECT id, name, institution, account_type
        FROM accounts WHERE id=:id AND user_id=:uid
    """), {"id": account_id, "uid": current_user.id}).mappings().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    selected_year = year or utcnow().date().year
    selected_start = date(selected_year, 1, 1)
    selected_end = date(selected_year, 12, 31)
    batches = db.execute(text("""
        SELECT id, filename, source_type, source_institution, parser_profile,
               created_at, transaction_span_start, transaction_span_end,
               coverage_status, coverage_start, coverage_end, imported_count,
               duplicate_count, failed_count, archived_at
        FROM import_batches
        WHERE user_id=:uid AND account_id=:account_id
        ORDER BY created_at
    """), {"uid": current_user.id, "account_id": account_id}).mappings().all()
    ranges: list[dict[str, Any]] = []
    confirmed: list[tuple[date, date]] = []
    uncertain: list[tuple[date, date]] = []
    for batch in batches:
        span_start = _as_date(batch.get("transaction_span_start"))
        span_end = _as_date(batch.get("transaction_span_end"))
        coverage_start = _as_date(batch.get("coverage_start"))
        coverage_end = _as_date(batch.get("coverage_end"))
        status_value = batch.get("coverage_status") or "unknown"
        if status_value == "confirmed" and coverage_start and coverage_end:
            confirmed.append((coverage_start, coverage_end))
        elif status_value == "partial" and coverage_start and coverage_end:
            uncertain.append((coverage_start, coverage_end))
        visible_start = coverage_start or span_start
        visible_end = coverage_end or span_end
        if visible_start and visible_end and _ranges_overlap(
            (visible_start, visible_end),
            (selected_start, selected_end),
        ):
            ranges.append({
                "batch_id": batch["id"],
                "filename": batch["filename"],
                "source_type": batch.get("source_type") or "csv_import",
                "source_institution": batch.get("source_institution"),
                "parser_profile": batch.get("parser_profile"),
                "coverage_status": status_value,
                "transaction_span_start": span_start.isoformat() if span_start else None,
                "transaction_span_end": span_end.isoformat() if span_end else None,
                "coverage_start": coverage_start.isoformat() if coverage_start else None,
                "coverage_end": coverage_end.isoformat() if coverage_end else None,
                "transaction_count": batch["imported_count"],
                "duplicate_count": batch["duplicate_count"],
                "failed_count": batch["failed_count"],
                "imported_at": str(batch["created_at"]),
                "archived": bool(batch.get("archived_at")),
            })
    gap_rows = db.execute(text("""
        SELECT id, start_date, end_date, reason, source_batch_id
        FROM known_coverage_gaps
        WHERE user_id=:uid AND account_id=:account_id
          AND end_date>=:start AND start_date<=:end
        ORDER BY start_date
    """), {
        "uid": current_user.id,
        "account_id": account_id,
        "start": selected_start,
        "end": selected_end,
    }).mappings().all()
    known_gaps = [(_as_date(row["start_date"]), _as_date(row["end_date"])) for row in gap_rows]
    known_gap_ranges = [
        (start, end)
        for start, end in known_gaps
        if start is not None and end is not None
    ]
    visible_confirmed = [
        (max(start, selected_start), min(end, selected_end))
        for start, end in confirmed
        if _ranges_overlap((start, end), (selected_start, selected_end))
    ]
    merged = _merge_intervals(visible_confirmed)
    detected_gaps = _gaps_between(merged)
    quality = _coverage_quality(
        confirmed,
        selected_start,
        selected_end,
        uncertain=uncertain,
        known_gaps=known_gap_ranges,
    )
    latest_batch = max(batches, key=lambda item: item["created_at"], default=None)
    return {
        "account": dict(account),
        "year": selected_year,
        "current_threshold_days": CURRENT_COVERAGE_THRESHOLD_DAYS,
        "quality": quality,
        "confirmed_ranges": [
            {"start": start.isoformat(), "end": end.isoformat()}
            for start, end in merged
        ],
        "detected_gaps": [
            {"start": start.isoformat(), "end": end.isoformat(), "state": "unknown_gap"}
            for start, end in detected_gaps
        ],
        "known_gaps": [
            {
                "id": row["id"],
                "start": str(row["start_date"]),
                "end": str(row["end_date"]),
                "reason": row["reason"],
                "source_batch_id": row["source_batch_id"],
            }
            for row in gap_rows
        ],
        "source_ranges": ranges,
        "latest_import": (
            {
                "id": latest_batch["id"],
                "filename": latest_batch["filename"],
                "created_at": str(latest_batch["created_at"]),
            }
            if latest_batch
            else None
        ),
        "month_position_helper": (
            "Day positions use the real number of days in each calendar month, including leap years."
        ),
    }


@router.get("/v11/coverage")
def household_coverage(
    year: int | None = Query(None, ge=2000, le=2200),
    current_user: User = USER,
    db: DbSession = DB,
):
    selected_year = year or utcnow().date().year
    accounts = db.execute(text("""
        SELECT id FROM accounts
        WHERE user_id=:uid AND is_active=1
        ORDER BY name
    """), {"uid": current_user.id}).mappings().all()
    return {
        "year": selected_year,
        "accounts": [
            account_coverage(row["id"], selected_year, current_user, db)
            for row in accounts
        ],
    }


@router.get("/v11/coverage/month-position")
def month_position(value: date):
    return {
        "date": value.isoformat(),
        "month": value.month,
        "percent": round(_month_day_percent(value), 6),
    }


def _transaction(db: DbSession, user: User, transaction_id: int) -> dict[str, Any]:
    row = db.execute(text("""
        SELECT id, account_id, amount_cents, import_batch_id, external_id,
               reconciliation_state, transaction_date, description
        FROM transactions
        WHERE id=:id AND user_id=:uid
    """), {"id": transaction_id, "uid": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return dict(row)


@router.get("/v11/transactions/{transaction_id}/splits")
def transaction_splits(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    transaction = _transaction(db, current_user, transaction_id)
    rows = db.execute(text("""
        SELECT * FROM transaction_splits
        WHERE transaction_id=:transaction_id AND user_id=:uid
        ORDER BY id
    """), {"transaction_id": transaction_id, "uid": current_user.id}).mappings().all()
    allocated = sum(int(row["amount_cents"]) for row in rows)
    authoritative = abs(int(transaction["amount_cents"]))
    return {
        "transaction_id": transaction_id,
        "transaction_amount": cents_to_decimal(authoritative),
        "allocated": cents_to_decimal(allocated),
        "remaining": cents_to_decimal(authoritative - allocated),
        "provenance": {
            "import_batch_id": transaction.get("import_batch_id"),
            "external_id": transaction.get("external_id"),
            "reconciliation_state": transaction.get("reconciliation_state"),
        },
        "items": [
            {**dict(row), "amount": cents_to_decimal(row["amount_cents"])}
            for row in rows
        ],
    }


@router.put("/v11/transactions/{transaction_id}/splits")
def save_transaction_splits(
    transaction_id: int,
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
):
    transaction = _transaction(db, current_user, transaction_id)
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        raise HTTPException(status_code=400, detail="At least one split allocation is required")
    existing_ids = {
        int(row[0])
        for row in db.execute(text("""
            SELECT id FROM transaction_splits
            WHERE transaction_id=:transaction_id AND user_id=:uid
        """), {"transaction_id": transaction_id, "uid": current_user.id}).all()
    }
    parsed: list[dict[str, Any]] = []
    total = 0
    for index, item in enumerate(raw_items, start=1):
        amount_cents = abs(parse_money(item.get("amount")))
        if amount_cents <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Split allocation {index} must be greater than zero",
            )
        allocation_id = int(item["id"]) if item.get("id") else None
        if allocation_id is not None and allocation_id not in existing_ids:
            raise HTTPException(status_code=400, detail=f"Split allocation {index} is invalid")
        category_id = item.get("category_id")
        category_name = item.get("category") or item.get("category_name")
        if category_id:
            category = db.execute(text("""
                SELECT id, name FROM categories
                WHERE id=:id AND user_id=:uid AND is_active=1
            """), {"id": int(category_id), "uid": current_user.id}).mappings().first()
            if not category:
                raise HTTPException(
                    status_code=400,
                    detail=f"Split allocation {index} has an invalid Category",
                )
            category_name = category["name"]
        if not category_name:
            raise HTTPException(
                status_code=400,
                detail=f"Split allocation {index} requires a Category",
            )
        parsed.append({
            "id": allocation_id,
            "amount_cents": amount_cents,
            "category_id": int(category_id) if category_id else None,
            "category_name": str(category_name)[:180],
            "notes": str(item.get("notes") or "")[:500] or None,
        })
        total += amount_cents
    authoritative = abs(int(transaction["amount_cents"]))
    if total != authoritative:
        raise HTTPException(
            status_code=400,
            detail=(
                "Split allocations must equal the transaction amount. "
                f"Remaining: {cents_to_decimal(authoritative - total)}"
            ),
        )
    now = utcnow()
    kept_ids: set[int] = set()
    for item in parsed:
        allocation_id = item.pop("id")
        if allocation_id is None:
            db.execute(text("""
                INSERT INTO transaction_splits (
                    user_id, transaction_id, amount_cents, category_id,
                    category_name, notes, created_at, updated_at
                ) VALUES (
                    :uid, :transaction_id, :amount_cents, :category_id,
                    :category_name, :notes, :now, :now
                )
            """), {
                "uid": current_user.id,
                "transaction_id": transaction_id,
                "now": now,
                **item,
            })
            kept_ids.add(int(db.execute(text("SELECT last_insert_rowid()")).scalar()))
        else:
            kept_ids.add(allocation_id)
            db.execute(text("""
                UPDATE transaction_splits
                SET amount_cents=:amount_cents, category_id=:category_id,
                    category_name=:category_name, notes=:notes, updated_at=:now
                WHERE id=:id AND transaction_id=:transaction_id AND user_id=:uid
            """), {
                "id": allocation_id,
                "transaction_id": transaction_id,
                "uid": current_user.id,
                "now": now,
                **item,
            })
    for allocation_id in existing_ids - kept_ids:
        db.execute(
            text("DELETE FROM transaction_splits WHERE id=:id AND user_id=:uid"),
            {"id": allocation_id, "uid": current_user.id},
        )
    db.execute(text("""
        UPDATE transactions SET updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"now": now, "id": transaction_id, "uid": current_user.id})
    db.commit()
    return transaction_splits(transaction_id, current_user, db)


@router.delete(
    "/v11/transactions/{transaction_id}/splits",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_transaction_splits(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    _transaction(db, current_user, transaction_id)
    db.execute(text("""
        DELETE FROM transaction_splits
        WHERE transaction_id=:transaction_id AND user_id=:uid
    """), {"transaction_id": transaction_id, "uid": current_user.id})
    db.commit()


def _split_aware_actual_for_categories(
    db: DbSession,
    user: User,
    names: set[str],
    start: date,
    end: date,
    direction: str,
) -> tuple[int, int]:
    if not names:
        return 0, 0
    placeholders = {f"category_{index}": name for index, name in enumerate(names)}
    in_clause = ",".join(f":{key}" for key in placeholders)
    transaction_type = "income" if direction == "income" else "expense"
    split_rows = db.execute(text(f"""
        SELECT t.id AS transaction_id, s.amount_cents
        FROM transaction_splits s
        JOIN transactions t ON t.id=s.transaction_id AND t.user_id=s.user_id
        WHERE t.user_id=:uid AND t.transaction_type=:transaction_type
          AND t.transaction_date BETWEEN :start AND :end
          AND s.category_name IN ({in_clause})
    """), {
        "uid": user.id,
        "transaction_type": transaction_type,
        "start": start,
        "end": end,
        **placeholders,
    }).mappings().all()
    unsplit_rows = db.execute(text(f"""
        SELECT t.id AS transaction_id, ABS(t.amount_cents) AS amount_cents
        FROM transactions t
        WHERE t.user_id=:uid AND t.transaction_type=:transaction_type
          AND t.transaction_date BETWEEN :start AND :end
          AND t.category IN ({in_clause})
          AND NOT EXISTS (
              SELECT 1 FROM transaction_splits s
              WHERE s.user_id=t.user_id AND s.transaction_id=t.id
          )
    """), {
        "uid": user.id,
        "transaction_type": transaction_type,
        "start": start,
        "end": end,
        **placeholders,
    }).mappings().all()
    transaction_ids = {
        int(row["transaction_id"])
        for row in [*split_rows, *unsplit_rows]
    }
    total = sum(abs(int(row["amount_cents"] or 0)) for row in split_rows)
    total += sum(abs(int(row["amount_cents"] or 0)) for row in unsplit_rows)
    return total, len(transaction_ids)


def _split_aware_unbudgeted(
    db: DbSession,
    user: User,
    start: date,
    end: date,
) -> list[dict[str, Any]]:
    budgeted = {
        row[0]
        for row in db.execute(text("""
            SELECT category_name FROM budgets
            WHERE user_id=:uid AND is_active=1 AND category_name IS NOT NULL
        """), {"uid": user.id}).all()
    }
    rows = db.execute(text("""
        SELECT category, COUNT(DISTINCT transaction_id) AS count,
               COALESCE(SUM(amount_cents), 0) AS total
        FROM (
            SELECT s.category_name AS category, t.id AS transaction_id,
                   s.amount_cents AS amount_cents
            FROM transaction_splits s
            JOIN transactions t ON t.id=s.transaction_id AND t.user_id=s.user_id
            WHERE t.user_id=:uid AND t.transaction_type='expense'
              AND t.transaction_date BETWEEN :start AND :end
              AND s.category_name IS NOT NULL AND s.category_name!=''
            UNION ALL
            SELECT t.category AS category, t.id AS transaction_id,
                   ABS(t.amount_cents) AS amount_cents
            FROM transactions t
            WHERE t.user_id=:uid AND t.transaction_type='expense'
              AND t.transaction_date BETWEEN :start AND :end
              AND t.category IS NOT NULL AND t.category!=''
              AND NOT EXISTS (
                  SELECT 1 FROM transaction_splits s
                  WHERE s.user_id=t.user_id AND s.transaction_id=t.id
              )
        ) activity
        GROUP BY category
        ORDER BY total DESC
    """), {"uid": user.id, "start": start, "end": end}).mappings().all()
    return [
        {
            "category": row["category"],
            "actual": cents_to_decimal(abs(int(row["total"] or 0))),
            "transaction_count": int(row["count"] or 0),
            "historical_average_weekly": None,
            "action": "create_budget",
        }
        for row in rows
        if row["category"] not in budgeted
    ]


budget_module._actual_for_categories = _split_aware_actual_for_categories
budget_module.find_unbudgeted_categories = _split_aware_unbudgeted
legacy_v09.analyse_budgets = budget_module.analyse_budgets


def _generate_mfa_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(secret.upper() + padding)


def _totp(secret: str, at_time: int | None = None) -> str:
    timestamp = int(at_time if at_time is not None else time.time())
    counter = timestamp // 30
    digest = hmac.new(
        _decode_secret(secret),
        struct.pack(">Q", counter),
        hashlib.sha1,
    ).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 1_000_000:06d}"


def _verify_totp(secret: str, code: str) -> bool:
    cleaned = "".join(character for character in str(code) if character.isdigit())
    if len(cleaned) != 6:
        return False
    now = int(time.time())
    return any(
        hmac.compare_digest(_totp(secret, now + offset * 30), cleaned)
        for offset in (-1, 0, 1)
    )


def _mfa_row(db: DbSession, user_id: int) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM mfa_settings WHERE user_id=:uid"),
        {"uid": user_id},
    ).mappings().first()
    return dict(row) if row else None


def _mfa_enabled(db: DbSession, user_id: int) -> bool:
    row = _mfa_row(db, user_id)
    return bool(row and row.get("enabled") and row.get("secret"))


def _admin_recovery_bypass(user: User) -> bool:
    return bool(user.is_admin and get_settings().admin_recovery_mode)


def _recovery_hash(code: str) -> str:
    return hash_token(str(code).replace("-", "").strip().upper())


def _generate_recovery_codes(count: int = 10) -> list[str]:
    return [
        f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        for _ in range(count)
    ]


def _store_recovery_codes(db: DbSession, user_id: int, codes: list[str]) -> None:
    now = utcnow()
    db.execute(text("DELETE FROM mfa_recovery_codes WHERE user_id=:uid"), {"uid": user_id})
    for code in codes:
        db.execute(text("""
            INSERT INTO mfa_recovery_codes (user_id, code_hash, used_at, created_at)
            VALUES (:uid, :code_hash, NULL, :now)
        """), {"uid": user_id, "code_hash": _recovery_hash(code), "now": now})


def _verify_recovery_code(db: DbSession, user_id: int, code: str) -> bool:
    code_hash = _recovery_hash(code)
    row = db.execute(text("""
        SELECT id FROM mfa_recovery_codes
        WHERE user_id=:uid AND code_hash=:code_hash AND used_at IS NULL
        LIMIT 1
    """), {"uid": user_id, "code_hash": code_hash}).mappings().first()
    if not row:
        return False
    db.execute(text("""
        UPDATE mfa_recovery_codes SET used_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"now": utcnow(), "id": row["id"], "uid": user_id})
    return True


def _verify_second_factor(db: DbSession, user_id: int, code: str) -> bool:
    row = _mfa_row(db, user_id)
    if not row or not row.get("enabled") or not row.get("secret"):
        return False
    if _verify_totp(str(row["secret"]), code):
        return True
    return _verify_recovery_code(db, user_id, code)


def _create_login_challenge(db: DbSession, user_id: int) -> str:
    token = new_session_token()
    now = utcnow()
    db.execute(text("""
        DELETE FROM mfa_login_challenges
        WHERE user_id=:uid AND (used_at IS NOT NULL OR expires_at<:now)
    """), {"uid": user_id, "now": now})
    db.execute(text("""
        INSERT INTO mfa_login_challenges (
            user_id, token_hash, expires_at, used_at, created_at
        ) VALUES (
            :uid, :token_hash, :expires_at, NULL, :now
        )
    """), {
        "uid": user_id,
        "token_hash": hash_token(token),
        "expires_at": now + timedelta(minutes=MFA_CHALLENGE_MINUTES),
        "now": now,
    })
    db.commit()
    return token


def _public_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": bool(user.is_admin),
    }


def _revoke_other_sessions(db: DbSession, user_id: int, current_token: str | None) -> int:
    now = utcnow()
    if current_token:
        result = db.execute(text("""
            UPDATE sessions SET revoked_at=:now
            WHERE user_id=:uid AND revoked_at IS NULL AND token_hash!=:current_hash
        """), {
            "now": now,
            "uid": user_id,
            "current_hash": hash_token(current_token),
        })
    else:
        result = db.execute(text("""
            UPDATE sessions SET revoked_at=:now
            WHERE user_id=:uid AND revoked_at IS NULL
        """), {"now": now, "uid": user_id})
    return int(result.rowcount or 0)


@router.post("/auth/login")
def login_v11(
    payload: dict[str, Any],
    request: Request,
    response: Response,
    db: DbSession = DB,
):
    username = str(payload.get("username") or "")
    password = str(payload.get("password") or "")
    user = auth_module.authenticate_user(db, username, password, get_client_key(request))
    if _mfa_enabled(db, user.id) and not _admin_recovery_bypass(user):
        challenge = _create_login_challenge(db, user.id)
        response.status_code = status.HTTP_202_ACCEPTED
        return {
            "mfa_required": True,
            "challenge_token": challenge,
            "expires_in_seconds": MFA_CHALLENGE_MINUTES * 60,
        }
    start_session(response, db, user)
    return {**_public_user(user), "mfa_required": False}


@router.post("/v11/auth/mfa-challenge")
def complete_mfa_login(
    payload: dict[str, Any],
    response: Response,
    db: DbSession = DB,
):
    challenge_token = str(payload.get("challenge_token") or "")
    code = str(payload.get("code") or "")
    if not challenge_token or not code:
        raise HTTPException(status_code=400, detail="Challenge token and MFA code are required")
    now = utcnow()
    challenge = db.execute(text("""
        SELECT * FROM mfa_login_challenges
        WHERE token_hash=:token_hash AND used_at IS NULL
        LIMIT 1
    """), {"token_hash": hash_token(challenge_token)}).mappings().first()
    if not challenge:
        raise HTTPException(status_code=401, detail="MFA challenge is invalid or already used")
    expires_at = _as_datetime(challenge["expires_at"])
    if expires_at is None or expires_at <= now:
        raise HTTPException(status_code=401, detail="MFA challenge has expired")
    user = db.execute(text("""
        SELECT * FROM users WHERE id=:id AND is_active=1
    """), {"id": challenge["user_id"]}).mappings().first()
    if not user:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    if not _verify_second_factor(db, int(user["id"]), code):
        raise HTTPException(status_code=401, detail="Invalid MFA code")
    db.execute(text("""
        UPDATE mfa_login_challenges SET used_at=:now
        WHERE id=:id
    """), {"now": now, "id": challenge["id"]})
    db.commit()
    user_model = db.get(User, int(user["id"]))
    if user_model is None:
        raise HTTPException(status_code=401, detail="Account is unavailable")
    start_session(response, db, user_model)
    return {**_public_user(user_model), "mfa_required": False}


@router.get("/v11/mfa/state")
def mfa_state(current_user: User = USER, db: DbSession = DB):
    row = _mfa_row(db, current_user.id)
    unused_codes = int(db.execute(text("""
        SELECT COUNT(*) FROM mfa_recovery_codes
        WHERE user_id=:uid AND used_at IS NULL
    """), {"uid": current_user.id}).scalar() or 0)
    return {
        "enabled": bool(row and row.get("enabled")),
        "pending_enrolment": bool(row and row.get("pending_secret")),
        "enabled_at": str(row.get("enabled_at")) if row and row.get("enabled_at") else None,
        "recovery_codes_remaining": unused_codes,
        "administrator_recovery_mode": _admin_recovery_bypass(current_user),
        "storage_model": (
            "TOTP secrets are stored only in Fynvo's protected local database. "
            "They are not logged or exposed by state APIs. The current deployment "
            "does not claim database-level encryption at rest."
        ),
    }


@router.post("/v11/mfa/enrol")
def enrol_mfa(current_user: User = USER, db: DbSession = DB):
    if _mfa_enabled(db, current_user.id):
        raise HTTPException(status_code=409, detail="MFA is already enabled")
    secret = _generate_mfa_secret()
    now = utcnow()
    db.execute(text("""
        INSERT INTO mfa_settings (user_id, enabled, secret, pending_secret, enabled_at, updated_at)
        VALUES (:uid, 0, NULL, :secret, NULL, :now)
        ON CONFLICT(user_id) DO UPDATE SET
            enabled=0, secret=NULL, pending_secret=:secret,
            enabled_at=NULL, updated_at=:now
    """), {"uid": current_user.id, "secret": secret, "now": now})
    db.commit()
    account_label = quote(current_user.username)
    issuer = quote(MFA_ISSUER)
    return {
        "secret": secret,
        "otpauth_uri": (
            f"otpauth://totp/{issuer}:{account_label}?secret={secret}"
            f"&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
        ),
        "message": "Verify a code from your authenticator before MFA is activated.",
    }


@router.post("/v11/mfa/activate")
def activate_mfa(
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
    session_token: str | None = SESSION,
):
    row = _mfa_row(db, current_user.id)
    pending = str(row.get("pending_secret") or "") if row else ""
    if not pending:
        raise HTTPException(status_code=400, detail="Start MFA enrolment first")
    if not _verify_totp(pending, str(payload.get("code") or "")):
        raise HTTPException(status_code=400, detail="Authenticator code is invalid")
    recovery_codes = _generate_recovery_codes()
    now = utcnow()
    db.execute(text("""
        UPDATE mfa_settings
        SET enabled=1, secret=:secret, pending_secret=NULL,
            enabled_at=:now, updated_at=:now
        WHERE user_id=:uid
    """), {"secret": pending, "now": now, "uid": current_user.id})
    _store_recovery_codes(db, current_user.id, recovery_codes)
    revoked = _revoke_other_sessions(db, current_user.id, session_token)
    db.commit()
    return {
        "enabled": True,
        "recovery_codes": recovery_codes,
        "recovery_codes_message": "Store these recovery codes securely. They are shown only once.",
        "other_sessions_revoked": revoked,
    }


@router.post("/v11/mfa/recovery/regenerate")
def regenerate_recovery_codes(
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
):
    if not _verify_second_factor(db, current_user.id, str(payload.get("code") or "")):
        raise HTTPException(status_code=400, detail="A valid MFA or recovery code is required")
    codes = _generate_recovery_codes()
    _store_recovery_codes(db, current_user.id, codes)
    db.commit()
    return {
        "recovery_codes": codes,
        "message": "Previous unused recovery codes have been invalidated.",
    }


@router.post("/v11/mfa/disable")
def disable_mfa(
    payload: dict[str, Any],
    current_user: User = USER,
    db: DbSession = DB,
    session_token: str | None = SESSION,
):
    if not _mfa_enabled(db, current_user.id):
        return {"enabled": False, "other_sessions_revoked": 0}
    if not _verify_second_factor(db, current_user.id, str(payload.get("code") or "")):
        raise HTTPException(status_code=400, detail="A valid MFA or recovery code is required")
    db.execute(text("""
        UPDATE mfa_settings
        SET enabled=0, secret=NULL, pending_secret=NULL,
            enabled_at=NULL, updated_at=:now
        WHERE user_id=:uid
    """), {"now": utcnow(), "uid": current_user.id})
    db.execute(text("DELETE FROM mfa_recovery_codes WHERE user_id=:uid"), {"uid": current_user.id})
    db.execute(text("DELETE FROM mfa_login_challenges WHERE user_id=:uid"), {"uid": current_user.id})
    revoked = _revoke_other_sessions(db, current_user.id, session_token)
    db.commit()
    return {"enabled": False, "other_sessions_revoked": revoked}


@router.post("/v11/mfa/admin-recovery-reset")
def administrator_recovery_reset(
    current_user: User = USER,
    db: DbSession = DB,
    session_token: str | None = SESSION,
):
    if not current_user.is_admin or not get_settings().admin_recovery_mode:
        raise HTTPException(
            status_code=403,
            detail="Administrator recovery mode must be enabled in Home Assistant Configuration",
        )
    db.execute(text("DELETE FROM mfa_settings WHERE user_id=:uid"), {"uid": current_user.id})
    db.execute(text("DELETE FROM mfa_recovery_codes WHERE user_id=:uid"), {"uid": current_user.id})
    db.execute(text("DELETE FROM mfa_login_challenges WHERE user_id=:uid"), {"uid": current_user.id})
    revoked = _revoke_other_sessions(db, current_user.id, session_token)
    db.commit()
    return {
        "enabled": False,
        "recovery_reset": True,
        "other_sessions_revoked": revoked,
        "message": (
            "MFA was reset through administrator recovery mode. Disable admin_recovery_mode "
            "in Home Assistant Configuration after confirming normal access."
        ),
    }


EXPORT_TABLES = {
    "accounts": "accounts",
    "cards": "cards",
    "transactions": "transactions",
    "transaction_splits": "transaction_splits",
    "categories": "categories",
    "expense_types": "expense_types",
    "income": "income_sources",
    "bills": "bills",
    "recurring_expenses": "recurring_expenses",
    "planned_spending": "planned_spending",
    "budgets": "budgets",
    "goals": "goals",
    "goal_contributions": "goal_contributions",
    "scenarios": "forecast_scenarios",
    "import_batches": "import_batches",
    "import_row_diagnostics": "import_row_diagnostics",
    "coverage_gaps": "known_coverage_gaps",
    "reconciliation_links": "reconciliation_links",
}


def _export_rows(db: DbSession, user: User, table_name: str) -> list[dict[str, Any]]:
    if not _table_exists(db, table_name):
        return []
    rows = db.execute(
        text(f"SELECT * FROM {table_name} WHERE user_id=:uid ORDER BY id"),
        {"uid": user.id},
    ).mappings().all()
    return [dict(row) for row in rows]


def _record_export(db: DbSession, user_id: int, export_format: str, dataset: str) -> None:
    db.execute(text("""
        INSERT INTO data_exports (user_id, export_format, dataset, created_at)
        VALUES (:uid, :export_format, :dataset, :now)
    """), {
        "uid": user_id,
        "export_format": export_format,
        "dataset": dataset,
        "now": utcnow(),
    })


@router.get("/v11/exports/full")
def full_export(current_user: User = USER, db: DbSession = DB):
    payload: dict[str, Any] = {
        "exported_at": utcnow().isoformat(),
        "format": "fynvo-json-v1.1",
        "privacy_warning": (
            "This export contains sensitive financial information. Store it securely."
        ),
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
        },
        "relationships": {
            "transaction_import_provenance": "transactions.import_batch_id -> import_batches.id",
            "transaction_splits": "transaction_splits.transaction_id -> transactions.id",
            "account_cards": "cards.account_id -> accounts.id",
            "reconciliation": "reconciliation_links.transaction_id -> transactions.id",
        },
    }
    for key, table_name in EXPORT_TABLES.items():
        payload[key] = _export_rows(db, current_user, table_name)
    _record_export(db, current_user.id, "json", "full")
    db.commit()
    return payload


@router.get("/v11/exports/{dataset}.csv", response_class=PlainTextResponse)
def csv_export(dataset: str, current_user: User = USER, db: DbSession = DB):
    table_name = EXPORT_TABLES.get(dataset)
    if table_name is None:
        raise HTTPException(status_code=404, detail="Export dataset is not supported")
    rows = _export_rows(db, current_user, table_name)
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    _record_export(db, current_user.id, "csv", dataset)
    db.commit()
    response = PlainTextResponse(output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="fynvo-{dataset}.csv"'
    response.headers["Cache-Control"] = "no-store"
    return response
