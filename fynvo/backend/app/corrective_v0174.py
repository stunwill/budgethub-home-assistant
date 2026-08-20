from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .finance import list_recurring, schedule_summary, today_local
from .models import User
from .money import cents_to_decimal, parse_money
from .v1 import list_categories_v1

router = APIRouter(prefix="/corrective-v0174")
DB = Depends(get_db)
USER = Depends(get_current_user)


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _descendant_ids(categories: list[dict[str, Any]], category_id: int) -> set[int]:
    by_parent: dict[int, list[int]] = {}
    for item in categories:
        parent_id = item.get("parent_id")
        if parent_id is not None:
            by_parent.setdefault(int(parent_id), []).append(int(item["id"]))
    ids = {int(category_id)}
    stack = [int(category_id)]
    while stack:
        parent = stack.pop()
        for child_id in by_parent.get(parent, []):
            if child_id not in ids:
                ids.add(child_id)
                stack.append(child_id)
    return ids


def _category_activity(db: DbSession, user: User, category_ids: set[int], start: date, end: date) -> tuple[int, int]:
    if not category_ids:
        return 0, 0
    placeholders = ",".join(f":c{i}" for i, _ in enumerate(sorted(category_ids)))
    params: dict[str, Any] = {"uid": user.id, "start": start, "end": end}
    for i, cid in enumerate(sorted(category_ids)):
        params[f"c{i}"] = cid

    tx = db.execute(text(f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(ABS(amount_cents)),0) AS total
        FROM transactions
        WHERE user_id=:uid AND transaction_type='expense'
          AND transaction_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
    """), params).mappings().first()

    recurring = db.execute(text(f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(ABS(amount_cents)),0) AS total
        FROM recurring_expenses
        WHERE user_id=:uid AND is_active=1 AND category_id IN ({placeholders})
    """), params).mappings().first()

    planned = db.execute(text(f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(ABS(estimated_amount_cents)),0) AS total
        FROM planned_spending
        WHERE user_id=:uid AND status NOT IN ('cancelled','purchased')
          AND planned_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
    """), params).mappings().first()

    bills = db.execute(text(f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(ABS(remaining_amount_cents)),0) AS total
        FROM bills
        WHERE user_id=:uid AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL
          AND due_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
    """), params).mappings().first()

    count = sum(int((row or {}).get("count") or 0) for row in (tx, recurring, planned, bills))
    total = sum(int((row or {}).get("total") or 0) for row in (tx, recurring, planned, bills))
    return count, total


@router.get("/categories/summary")
def categories_summary(
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    start = today_local()
    end = start + timedelta(days=range_days)
    categories = list_categories_v1(db, current_user)
    children_by_parent: dict[int, list[dict[str, Any]]] = {}
    for item in categories:
        if item.get("parent_id") is not None:
            children_by_parent.setdefault(int(item["parent_id"]), []).append(item)

    result: list[dict[str, Any]] = []
    for item in categories:
        ids = _descendant_ids(categories, int(item["id"]))
        count, total = _category_activity(db, current_user, ids, start, end)
        result.append({
            **item,
            "entry_count": count,
            "total": cents_to_decimal(total),
            "child_count": len(children_by_parent.get(int(item["id"]), [])),
            "has_children": bool(children_by_parent.get(int(item["id"]))),
            "range_start": start.isoformat(),
            "range_end": end.isoformat(),
        })
    return result


@router.get("/categories/{category_id}/entries")
def category_entries(
    category_id: int,
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    start = today_local()
    end = start + timedelta(days=range_days)
    categories = list_categories_v1(db, current_user)
    ids = _descendant_ids(categories, category_id)
    placeholders = ",".join(f":c{i}" for i, _ in enumerate(sorted(ids)))
    params: dict[str, Any] = {"uid": current_user.id, "start": start, "end": end}
    for i, cid in enumerate(sorted(ids)):
        params[f"c{i}"] = cid

    rows: list[dict[str, Any]] = []
    for row in db.execute(text(f"""
        SELECT id,transaction_date AS date,description AS name,amount_cents,category,'transaction' AS source_type
        FROM transactions
        WHERE user_id=:uid AND transaction_type='expense' AND transaction_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
        ORDER BY transaction_date DESC,id DESC
    """), params).mappings().all():
        rows.append({**dict(row), "amount": cents_to_decimal(abs(int(row["amount_cents"] or 0)))})
    for row in db.execute(text(f"""
        SELECT id,next_due_date AS date,name,amount_cents,category,'recurring_expense' AS source_type
        FROM recurring_expenses
        WHERE user_id=:uid AND is_active=1 AND category_id IN ({placeholders})
        ORDER BY next_due_date,name
    """), params).mappings().all():
        rows.append({**dict(row), "amount": cents_to_decimal(abs(int(row["amount_cents"] or 0)))})
    for row in db.execute(text(f"""
        SELECT id,planned_date AS date,name,estimated_amount_cents AS amount_cents,category,'planned_spending' AS source_type
        FROM planned_spending
        WHERE user_id=:uid AND status NOT IN ('cancelled','purchased') AND planned_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
        ORDER BY planned_date,name
    """), params).mappings().all():
        rows.append({**dict(row), "amount": cents_to_decimal(abs(int(row["amount_cents"] or 0)))})
    return sorted(rows, key=lambda row: (str(row.get("date") or ""), str(row.get("name") or "")), reverse=True)


@router.get("/recurring/summary")
def recurring_summary(
    range_days: int = Query(90, ge=7, le=365),
    frequency: str = "all",
    db: DbSession = DB,
    current_user: User = USER,
):
    start = today_local()
    end = start + timedelta(days=range_days)
    rows = [item for item in list_recurring(db, current_user) if item.get("is_active")]
    if frequency != "all":
        rows = [item for item in rows if item.get("frequency") == frequency]
    allowed_ids = {int(item["id"]) for item in rows}
    schedule = schedule_summary(db, current_user, start, end)
    events = [
        event for event in schedule.get("events", [])
        if event.get("kind") == "recurring_expense"
        and event.get("source_id") is not None
        and int(event["source_id"]) in allowed_ids
    ]
    total_cents = sum(abs(parse_money(event.get("amount") or "0.00")) for event in events)
    return {
        "range_days": range_days,
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "frequency": frequency,
        "total": cents_to_decimal(total_cents),
        "occurrence_count": len(events),
        "recurring_count": len(rows),
        "items": rows,
    }
