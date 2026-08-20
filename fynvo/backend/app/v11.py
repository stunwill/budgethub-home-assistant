from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter(prefix="/api/v11")
DB = Depends(get_db)
USER = Depends(get_current_user)
COVERAGE_STATUSES = {"unknown", "partial", "confirmed"}


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid date") from exc


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


def _coverage_quality(confirmed: list[tuple[date, date]], selected_start: date, selected_end: date) -> dict[str, Any]:
    if not confirmed:
        return {"status": "no_data", "reason": "No confirmed imported or synchronised Actual source coverage exists."}
    merged = _merge_intervals(confirmed)
    gaps: list[dict[str, str]] = []
    cursor = selected_start
    for start, end in merged:
        if end < selected_start or start > selected_end:
            continue
        bounded_start = max(start, selected_start)
        bounded_end = min(end, selected_end)
        if bounded_start > cursor:
            gaps.append({"start": cursor.isoformat(), "end": (bounded_start - timedelta(days=1)).isoformat()})
        cursor = max(cursor, bounded_end + timedelta(days=1))
    if cursor <= selected_end:
        gaps.append({"start": cursor.isoformat(), "end": selected_end.isoformat()})
    latest_end = max(end for _, end in merged)
    today = utcnow().date()
    if not gaps and latest_end >= today - timedelta(days=3):
        return {"status": "current", "reason": "Confirmed source coverage is continuous and extends to within 3 calendar days of today.", "gaps": []}
    if not gaps:
        return {"status": "continuous", "reason": "Confirmed source coverage is continuous across the selected range.", "gaps": []}
    first_gap = gaps[0]
    return {"status": "partial", "reason": f"Coverage contains {len(gaps)} gap{'s' if len(gaps) != 1 else ''}; first gap {first_gap['start']} to {first_gap['end']}.", "gaps": gaps}


@router.get("/imports/{batch_id}")
def import_detail(batch_id: int, current_user: User = USER, db: DbSession = DB):
    batch = db.execute(text("SELECT * FROM import_batches WHERE id=:id AND user_id=:user_id"), {"id": batch_id, "user_id": current_user.id}).mappings().first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    rows = db.execute(text("SELECT id, account_id, transaction_date, amount_cents, transaction_type, description, merchant, category, status, reconciliation_state FROM transactions WHERE user_id=:user_id AND import_batch_id=:batch ORDER BY transaction_date, id"), {"user_id": current_user.id, "batch": str(batch_id)}).mappings().all()
    credit_cents = sum(abs(row["amount_cents"]) for row in rows if row["transaction_type"] == "income" or row["amount_cents"] > 0)
    debit_cents = sum(abs(row["amount_cents"]) for row in rows if not (row["transaction_type"] == "income" or row["amount_cents"] > 0))
    return {
        "id": batch["id"],
        "filename": batch["filename"],
        "account_id": batch["account_id"],
        "source_type": batch.get("source_type") or "csv",
        "source_institution": batch.get("source_institution"),
        "created_at": str(batch["created_at"]),
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
        "transactions": [{**dict(row), "amount": cents_to_decimal(row["amount_cents"])} for row in rows],
    }


@router.put("/imports/{batch_id}/coverage")
def set_import_coverage(batch_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    batch = db.execute(text("SELECT * FROM import_batches WHERE id=:id AND user_id=:user_id"), {"id": batch_id, "user_id": current_user.id}).mappings().first()
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
            raise HTTPException(status_code=400, detail="Confirmed coverage requires a start and end date")
    if start and end and end < start:
        raise HTTPException(status_code=400, detail="Coverage end must be on or after coverage start")
    now = utcnow()
    db.execute(text("UPDATE import_batches SET coverage_status=:status, coverage_start=:start, coverage_end=:end, coverage_note=:note, coverage_confirmed_at=:confirmed_at, coverage_confirmed_by=:confirmed_by, updated_at=:now WHERE id=:id AND user_id=:user_id"), {
        "status": coverage_status,
        "start": start,
        "end": end,
        "note": str(payload.get("coverage_note") or "")[:500] or None,
        "confirmed_at": now if coverage_status == "confirmed" else None,
        "confirmed_by": current_user.id if coverage_status == "confirmed" else None,
        "now": now,
        "id": batch_id,
        "user_id": current_user.id,
    })
    db.commit()
    return {"status": "ok", "batch_id": batch_id, "coverage_status": coverage_status, "coverage_start": start.isoformat() if start else None, "coverage_end": end.isoformat() if end else None}


@router.get("/coverage/accounts/{account_id}")
def account_coverage(account_id: int, year: int | None = Query(None, ge=2000, le=2200), current_user: User = USER, db: DbSession = DB):
    account = db.execute(text("SELECT id, name FROM accounts WHERE id=:id AND user_id=:user_id"), {"id": account_id, "user_id": current_user.id}).mappings().first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    selected_year = year or utcnow().date().year
    selected_start = date(selected_year, 1, 1)
    selected_end = date(selected_year, 12, 31)
    batches = db.execute(text("SELECT id, filename, source_type, created_at, transaction_span_start, transaction_span_end, coverage_status, coverage_start, coverage_end, imported_count FROM import_batches WHERE user_id=:user_id AND account_id=:account_id ORDER BY created_at"), {"user_id": current_user.id, "account_id": account_id}).mappings().all()
    ranges = []
    confirmed: list[tuple[date, date]] = []
    for batch in batches:
        span_start = _as_date(batch.get("transaction_span_start"))
        span_end = _as_date(batch.get("transaction_span_end"))
        cov_start = _as_date(batch.get("coverage_start"))
        cov_end = _as_date(batch.get("coverage_end"))
        if batch["coverage_status"] == "confirmed" and cov_start and cov_end:
            confirmed.append((cov_start, cov_end))
        visible_start = cov_start or span_start
        visible_end = cov_end or span_end
        if visible_start and visible_end and visible_end >= selected_start and visible_start <= selected_end:
            ranges.append({
                "batch_id": batch["id"],
                "filename": batch["filename"],
                "source_type": batch.get("source_type") or "csv",
                "coverage_status": batch.get("coverage_status") or "unknown",
                "transaction_span_start": span_start.isoformat() if span_start else None,
                "transaction_span_end": span_end.isoformat() if span_end else None,
                "coverage_start": cov_start.isoformat() if cov_start else None,
                "coverage_end": cov_end.isoformat() if cov_end else None,
                "imported_count": batch["imported_count"],
                "created_at": str(batch["created_at"]),
            })
    merged = _merge_intervals([(max(start, selected_start), min(end, selected_end)) for start, end in confirmed if end >= selected_start and start <= selected_end])
    quality = _coverage_quality(confirmed, selected_start, selected_end)
    return {
        "account": dict(account),
        "year": selected_year,
        "current_threshold_days": 3,
        "quality": quality,
        "confirmed_ranges": [{"start": start.isoformat(), "end": end.isoformat()} for start, end in merged],
        "source_ranges": ranges,
        "month_position_helper": "Day positions are calculated using the real number of days in each calendar month.",
    }


@router.get("/coverage")
def household_coverage(year: int | None = Query(None, ge=2000, le=2200), current_user: User = USER, db: DbSession = DB):
    selected_year = year or utcnow().date().year
    accounts = db.execute(text("SELECT id, name, institution, account_type FROM accounts WHERE user_id=:user_id AND is_active=1 ORDER BY name"), {"user_id": current_user.id}).mappings().all()
    return {"year": selected_year, "accounts": [account_coverage(row["id"], selected_year, current_user, db) for row in accounts]}


@router.get("/transactions/{transaction_id}/splits")
def transaction_splits(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    transaction = db.execute(text("SELECT id, amount_cents FROM transactions WHERE id=:id AND user_id=:user_id"), {"id": transaction_id, "user_id": current_user.id}).mappings().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    rows = db.execute(text("SELECT * FROM transaction_splits WHERE transaction_id=:transaction_id AND user_id=:user_id ORDER BY id"), {"transaction_id": transaction_id, "user_id": current_user.id}).mappings().all()
    allocated = sum(row["amount_cents"] for row in rows)
    return {"transaction_id": transaction_id, "transaction_amount": cents_to_decimal(abs(transaction["amount_cents"])), "allocated": cents_to_decimal(allocated), "remaining": cents_to_decimal(abs(transaction["amount_cents"]) - allocated), "items": [{**dict(row), "amount": cents_to_decimal(row["amount_cents"])} for row in rows]}


@router.put("/transactions/{transaction_id}/splits")
def save_transaction_splits(transaction_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    transaction = db.execute(text("SELECT id, amount_cents FROM transactions WHERE id=:id AND user_id=:user_id"), {"id": transaction_id, "user_id": current_user.id}).mappings().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        raise HTTPException(status_code=400, detail="At least one split allocation is required")
    parsed = []
    total = 0
    for index, item in enumerate(raw_items, start=1):
        amount_cents = abs(parse_money(item.get("amount")))
        if amount_cents <= 0:
            raise HTTPException(status_code=400, detail=f"Split allocation {index} must be greater than zero")
        category_id = item.get("category_id")
        category_name = item.get("category") or item.get("category_name")
        if category_id:
            category = db.execute(text("SELECT id, name FROM categories WHERE id=:id AND user_id=:user_id AND is_active=1"), {"id": int(category_id), "user_id": current_user.id}).mappings().first()
            if not category:
                raise HTTPException(status_code=400, detail=f"Split allocation {index} has an invalid Category")
            category_name = category["name"]
        parsed.append({"amount_cents": amount_cents, "category_id": int(category_id) if category_id else None, "category_name": category_name, "notes": str(item.get("notes") or "")[:500] or None})
        total += amount_cents
    authoritative = abs(transaction["amount_cents"])
    if total != authoritative:
        raise HTTPException(status_code=400, detail=f"Split allocations must equal the transaction amount. Remaining: {cents_to_decimal(authoritative - total)}")
    now = utcnow()
    db.execute(text("DELETE FROM transaction_splits WHERE transaction_id=:transaction_id AND user_id=:user_id"), {"transaction_id": transaction_id, "user_id": current_user.id})
    for item in parsed:
        db.execute(text("INSERT INTO transaction_splits (user_id, transaction_id, amount_cents, category_id, category_name, notes, created_at, updated_at) VALUES (:user_id, :transaction_id, :amount_cents, :category_id, :category_name, :notes, :now, :now)"), {"user_id": current_user.id, "transaction_id": transaction_id, "now": now, **item})
    db.execute(text("UPDATE transactions SET updated_at=:now WHERE id=:id AND user_id=:user_id"), {"now": now, "id": transaction_id, "user_id": current_user.id})
    db.commit()
    return transaction_splits(transaction_id, current_user, db)


@router.delete("/transactions/{transaction_id}/splits", status_code=status.HTTP_204_NO_CONTENT)
def clear_transaction_splits(transaction_id: int, current_user: User = USER, db: DbSession = DB):
    db.execute(text("DELETE FROM transaction_splits WHERE transaction_id=:transaction_id AND user_id=:user_id"), {"transaction_id": transaction_id, "user_id": current_user.id})
    db.commit()
    return None


@router.get("/exports/full")
def full_export(current_user: User = USER, db: DbSession = DB):
    tables = [
        "accounts", "transactions", "transaction_splits", "categories", "income_sources", "recurring_expenses", "bills", "planned_spending", "budgets", "forecast_scenarios", "import_batches", "reconciliation_links"
    ]
    payload: dict[str, Any] = {"exported_at": utcnow().isoformat(), "format": "fynvo-json-v1", "user": {"id": current_user.id, "username": current_user.username, "display_name": current_user.display_name}}
    for table in tables:
        rows = db.execute(text(f"SELECT * FROM {table} WHERE user_id=:user_id ORDER BY id"), {"user_id": current_user.id}).mappings().all()
        payload[table] = [dict(row) for row in rows]
    return payload


@router.get("/coverage/month-position")
def month_position(value: date):
    return {"date": value.isoformat(), "month": value.month, "percent": round(_month_day_percent(value), 6)}
