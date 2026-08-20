from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .finance import list_recurring, today_local
from .models import User
from .money import cents_to_decimal
from .v1 import _occurrence_dates, list_categories_v1

router = APIRouter(prefix="/corrective-v0174")
DB = Depends(get_db)
USER = Depends(get_current_user)


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def _consolidate_categories(db: DbSession, user: User) -> None:
    """Merge the two overlapping housing-maintenance categories without deleting history."""
    rows = [dict(row) for row in db.execute(text(
        "SELECT * FROM categories WHERE user_id=:uid ORDER BY id"
    ), {"uid": user.id}).mappings().all()]
    housing = next((row for row in rows if row.get("parent_id") is None and _norm(row.get("name")) == "housing"), None)
    if not housing:
        return
    children = [row for row in rows if row.get("parent_id") == housing["id"]]
    old_names = {"home maintenance", "home improvements", "house maintenance", "house improvements"}
    candidates = [row for row in children if _norm(row.get("name")) in old_names or _norm(row.get("name")) == "home maintenance & improvements"]
    if not candidates:
        return
    canonical = next((row for row in candidates if _norm(row.get("name")) == "home maintenance & improvements"), None)
    if canonical is None:
        canonical = candidates[0]
        db.execute(text("""
            UPDATE categories SET name='Home Maintenance & Improvements',is_active=1,updated_at=CURRENT_TIMESTAMP
            WHERE id=:id AND user_id=:uid
        """), {"id": canonical["id"], "uid": user.id})
    canonical_id = int(canonical["id"])
    canonical_path = "Housing → Home Maintenance & Improvements"
    duplicates = [row for row in candidates if int(row["id"]) != canonical_id]
    for duplicate in duplicates:
        duplicate_id = int(duplicate["id"])
        for table, value_column in (
            ("transactions", "category"),
            ("income_sources", "category"),
            ("recurring_expenses", "category"),
            ("planned_spending", "category"),
        ):
            db.execute(text(f"""
                UPDATE {table} SET category_id=:canonical, {value_column}=:path
                WHERE user_id=:uid AND category_id=:duplicate
            """), {"canonical": canonical_id, "duplicate": duplicate_id, "uid": user.id, "path": canonical_path})
        db.execute(text("""
            UPDATE bills SET category_id=:canonical,bill_type=:path
            WHERE user_id=:uid AND category_id=:duplicate
        """), {"canonical": canonical_id, "duplicate": duplicate_id, "uid": user.id, "path": canonical_path})
        db.execute(text("""
            UPDATE budgets SET category_id=:canonical,category_name=:path
            WHERE user_id=:uid AND category_id=:duplicate
        """), {"canonical": canonical_id, "duplicate": duplicate_id, "uid": user.id, "path": canonical_path})
        db.execute(text("""
            UPDATE categories SET is_active=0,notes=COALESCE(notes,'') || :note,updated_at=CURRENT_TIMESTAMP
            WHERE id=:id AND user_id=:uid
        """), {"id": duplicate_id, "uid": user.id, "note": "\nConsolidated into Home Maintenance & Improvements by v0.17.4."})
    for table, value_column in (
        ("transactions", "category"),
        ("income_sources", "category"),
        ("recurring_expenses", "category"),
        ("planned_spending", "category"),
    ):
        db.execute(text(f"""
            UPDATE {table} SET {value_column}=:path
            WHERE user_id=:uid AND category_id=:canonical
        """), {"canonical": canonical_id, "uid": user.id, "path": canonical_path})
    db.execute(text("UPDATE bills SET bill_type=:path WHERE user_id=:uid AND category_id=:canonical"), {"canonical": canonical_id, "uid": user.id, "path": canonical_path})
    db.execute(text("UPDATE budgets SET category_name=:path WHERE user_id=:uid AND category_id=:canonical"), {"canonical": canonical_id, "uid": user.id, "path": canonical_path})
    db.commit()


def _descendant_ids(categories: list[dict[str, Any]], category_id: int) -> set[int]:
    by_parent: dict[int, list[int]] = {}
    for item in categories:
        parent_id = item.get("parent_id")
        if parent_id is not None and item.get("is_active") is not False:
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


def _params_for_ids(user: User, category_ids: set[int], start: date, end: date) -> tuple[str, dict[str, Any]]:
    placeholders = ",".join(f":c{i}" for i, _ in enumerate(sorted(category_ids)))
    params: dict[str, Any] = {"uid": user.id, "start": start, "end": end}
    for i, cid in enumerate(sorted(category_ids)):
        params[f"c{i}"] = cid
    return placeholders, params


def _category_activity(db: DbSession, user: User, category_ids: set[int], start: date, end: date) -> tuple[int, int]:
    if not category_ids:
        return 0, 0
    placeholders, params = _params_for_ids(user, category_ids, start, end)
    tx = db.execute(text(f"""
        SELECT COUNT(*) AS count, COALESCE(SUM(ABS(amount_cents)),0) AS total
        FROM transactions
        WHERE user_id=:uid AND transaction_type='expense'
          AND transaction_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
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

    recurring_count = 0
    recurring_total = 0
    recurring_rows = db.execute(text(f"""
        SELECT * FROM recurring_expenses
        WHERE user_id=:uid AND is_active=1 AND category_id IN ({placeholders})
    """), params).mappings().all()
    for row in recurring_rows:
        if row.get("amount_cents") is None:
            continue
        for _when in _occurrence_dates(row.get("next_due_date"), start, end, row.get("frequency"), row.get("interval_count"), row.get("end_date")):
            recurring_count += 1
            recurring_total += abs(int(row["amount_cents"]))

    count = sum(int((row or {}).get("count") or 0) for row in (tx, planned, bills)) + recurring_count
    total = sum(int((row or {}).get("total") or 0) for row in (tx, planned, bills)) + recurring_total
    return count, total


@router.get("/categories/summary")
def categories_summary(
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    _consolidate_categories(db, current_user)
    start = today_local()
    end = start + timedelta(days=range_days)
    categories = [item for item in list_categories_v1(db, current_user) if item.get("is_active") is not False]
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
    _consolidate_categories(db, current_user)
    start = today_local()
    end = start + timedelta(days=range_days)
    categories = [item for item in list_categories_v1(db, current_user) if item.get("is_active") is not False]
    ids = _descendant_ids(categories, category_id)
    placeholders, params = _params_for_ids(current_user, ids, start, end)

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
        SELECT * FROM recurring_expenses
        WHERE user_id=:uid AND is_active=1 AND category_id IN ({placeholders})
    """), params).mappings().all():
        if row.get("amount_cents") is None:
            continue
        for when in _occurrence_dates(row.get("next_due_date"), start, end, row.get("frequency"), row.get("interval_count"), row.get("end_date")):
            rows.append({"id": row["id"], "date": when.isoformat(), "name": row["name"], "amount": cents_to_decimal(abs(int(row["amount_cents"]))), "category": row.get("category"), "source_type": "recurring_expense"})
    for row in db.execute(text(f"""
        SELECT id,planned_date AS date,name,estimated_amount_cents AS amount_cents,category,'planned_spending' AS source_type
        FROM planned_spending
        WHERE user_id=:uid AND status NOT IN ('cancelled','purchased') AND planned_date BETWEEN :start AND :end
          AND category_id IN ({placeholders})
        ORDER BY planned_date,name
    """), params).mappings().all():
        rows.append({**dict(row), "amount": cents_to_decimal(abs(int(row["amount_cents"] or 0)))})
    for row in db.execute(text(f"""
        SELECT id,due_date AS date,name,remaining_amount_cents AS amount_cents,bill_type AS category,'bill' AS source_type
        FROM bills
        WHERE user_id=:uid AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL
          AND due_date BETWEEN :start AND :end AND category_id IN ({placeholders})
        ORDER BY due_date,name
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
    raw_rows = db.execute(text("SELECT * FROM recurring_expenses WHERE user_id=:uid AND is_active=1"), {"uid": current_user.id}).mappings().all()
    total_cents = 0
    occurrence_count = 0
    for row in raw_rows:
        if int(row["id"]) not in allowed_ids or row.get("amount_cents") is None:
            continue
        for _when in _occurrence_dates(row.get("next_due_date"), start, end, row.get("frequency"), row.get("interval_count"), row.get("end_date")):
            occurrence_count += 1
            total_cents += abs(int(row["amount_cents"]))
    return {
        "range_days": range_days,
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "frequency": frequency,
        "total": cents_to_decimal(total_cents),
        "occurrence_count": occurrence_count,
        "recurring_count": len(rows),
        "items": rows,
    }
