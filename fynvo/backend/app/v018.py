from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .finance import schedule_summary, today_local
from .models import User
from .v1 import _sync_category_denormalized_values, list_categories_v1

router = APIRouter(prefix="/v018", tags=["v0.18 data integrity"])
DB = Depends(get_db)
USER = Depends(get_current_user)
CATEGORY_REFERENCE_TABLES = (
    "transactions",
    "income_sources",
    "recurring_expenses",
    "bills",
    "planned_spending",
    "budgets",
)
OUTGOING_KINDS = {"bill", "recurring_expense", "planned_spending"}


def normalise_category_name(value: str | None) -> str:
    """Return the authoritative comparison key for Category names."""
    return " ".join((value or "").strip().casefold().split())


def _category_row(db: DbSession, user: User, category_id: int) -> dict[str, Any]:
    row = db.execute(
        text("SELECT * FROM categories WHERE id=:id AND user_id=:uid"),
        {"id": category_id, "uid": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    return dict(row)


def assert_category_unique(
    db: DbSession,
    user: User,
    name: str | None,
    parent_id: int | None,
    exclude_id: int | None = None,
) -> None:
    needle = normalise_category_name(name)
    if not needle:
        raise HTTPException(status_code=400, detail="Category name is required")
    rows = db.execute(
        text(
            """
            SELECT id,name,parent_id
            FROM categories
            WHERE user_id=:uid
              AND ((parent_id IS NULL AND :parent_id IS NULL) OR parent_id=:parent_id)
            """
        ),
        {"uid": user.id, "parent_id": parent_id},
    ).mappings().all()
    for row in rows:
        if exclude_id is not None and int(row["id"]) == int(exclude_id):
            continue
        if normalise_category_name(row["name"]) == needle:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists under that parent",
            )


def _reference_counts(db: DbSession, user: User, category_id: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in CATEGORY_REFERENCE_TABLES:
        counts[table] = int(
            db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE user_id=:uid AND category_id=:cid"),
                {"uid": user.id, "cid": category_id},
            ).scalar()
            or 0
        )
    counts["children"] = int(
        db.execute(
            text("SELECT COUNT(*) FROM categories WHERE user_id=:uid AND parent_id=:cid AND is_active=1"),
            {"uid": user.id, "cid": category_id},
        ).scalar()
        or 0
    )
    return counts


def _descendant_ids(db: DbSession, user: User, category_id: int) -> set[int]:
    rows = db.execute(
        text("SELECT id,parent_id FROM categories WHERE user_id=:uid"),
        {"uid": user.id},
    ).mappings().all()
    children: dict[int, list[int]] = {}
    for row in rows:
        if row["parent_id"] is not None:
            children.setdefault(int(row["parent_id"]), []).append(int(row["id"]))
    result = {category_id}
    stack = [category_id]
    while stack:
        current = stack.pop()
        for child_id in children.get(current, []):
            if child_id not in result:
                result.add(child_id)
                stack.append(child_id)
    return result


def _reassign_category_references(
    db: DbSession,
    user: User,
    source_id: int,
    destination_id: int,
) -> None:
    for table in CATEGORY_REFERENCE_TABLES:
        db.execute(
            text(
                f"UPDATE {table} SET category_id=:destination "
                "WHERE user_id=:uid AND category_id=:source"
            ),
            {"destination": destination_id, "source": source_id, "uid": user.id},
        )


def _merge_duplicate_children(db: DbSession, user: User, parent_id: int) -> None:
    children = [
        dict(row)
        for row in db.execute(
            text(
                "SELECT * FROM categories "
                "WHERE user_id=:uid AND parent_id=:pid AND is_active=1 ORDER BY id"
            ),
            {"uid": user.id, "pid": parent_id},
        ).mappings().all()
    ]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for child in children:
        grouped.setdefault(normalise_category_name(child["name"]), []).append(child)
    for matches in grouped.values():
        if len(matches) < 2:
            continue
        destination_id = int(matches[0]["id"])
        for source in matches[1:]:
            source_id = int(source["id"])
            _reassign_category_references(db, user, source_id, destination_id)
            db.execute(
                text("UPDATE categories SET parent_id=:destination WHERE user_id=:uid AND parent_id=:source"),
                {"destination": destination_id, "source": source_id, "uid": user.id},
            )
            db.execute(
                text(
                    "UPDATE categories SET is_active=0,updated_at=CURRENT_TIMESTAMP,"
                    "notes=trim(COALESCE(notes,'') || :note) "
                    "WHERE id=:source AND user_id=:uid"
                ),
                {
                    "source": source_id,
                    "uid": user.id,
                    "note": f"\nMerged into category #{destination_id} by Fynvo v0.18.0.",
                },
            )


def merge_category(db: DbSession, user: User, source_id: int, destination_id: int) -> dict[str, Any]:
    if source_id == destination_id:
        raise HTTPException(status_code=400, detail="Source and destination categories must be different")
    source = _category_row(db, user, source_id)
    destination = _category_row(db, user, destination_id)
    if not source.get("is_active"):
        raise HTTPException(status_code=400, detail="Source category is already inactive")
    if not destination.get("is_active"):
        raise HTTPException(status_code=400, detail="Destination category must be active")
    if destination_id in _descendant_ids(db, user, source_id):
        raise HTTPException(status_code=400, detail="A category cannot be merged into one of its descendants")

    counts = _reference_counts(db, user, source_id)
    _reassign_category_references(db, user, source_id, destination_id)
    db.execute(
        text("UPDATE categories SET parent_id=:destination WHERE user_id=:uid AND parent_id=:source"),
        {"destination": destination_id, "source": source_id, "uid": user.id},
    )
    _merge_duplicate_children(db, user, destination_id)
    db.execute(
        text(
            "UPDATE categories SET is_active=0,updated_at=CURRENT_TIMESTAMP,"
            "notes=trim(COALESCE(notes,'') || :note) "
            "WHERE id=:source AND user_id=:uid"
        ),
        {
            "source": source_id,
            "uid": user.id,
            "note": f"\nMerged into category #{destination_id} by Fynvo v0.18.0.",
        },
    )
    _sync_category_denormalized_values(db, user)
    db.commit()
    return {
        "source": {"id": source_id, "name": source["name"]},
        "destination": {"id": destination_id, "name": destination["name"]},
        "reassigned": counts,
        "source_archived": True,
    }


def category_health(db: DbSession, user: User) -> dict[str, Any]:
    categories = [
        dict(row)
        for row in db.execute(
            text("SELECT * FROM categories WHERE user_id=:uid ORDER BY id"),
            {"uid": user.id},
        ).mappings().all()
    ]
    by_id = {int(row["id"]): row for row in categories}
    active = [row for row in categories if row.get("is_active")]

    duplicates: dict[tuple[int | None, str], list[dict[str, Any]]] = {}
    for row in active:
        parent_id = int(row["parent_id"]) if row.get("parent_id") is not None else None
        duplicates.setdefault((parent_id, normalise_category_name(row["name"])), []).append(row)
    duplicate_groups = [
        {
            "parent_id": key[0],
            "normalised_name": key[1],
            "categories": [{"id": int(item["id"]), "name": item["name"]} for item in rows],
        }
        for key, rows in duplicates.items()
        if key[1] and len(rows) > 1
    ]

    orphan_children = [
        {"id": int(row["id"]), "name": row["name"], "parent_id": int(row["parent_id"])}
        for row in active
        if row.get("parent_id") is not None and int(row["parent_id"]) not in by_id
    ]
    inactive_parent_children = [
        {"id": int(row["id"]), "name": row["name"], "parent_id": int(row["parent_id"])}
        for row in active
        if row.get("parent_id") is not None
        and int(row["parent_id"]) in by_id
        and not by_id[int(row["parent_id"])].get("is_active")
    ]

    cycles: list[list[int]] = []
    for row in active:
        start = int(row["id"])
        seen: list[int] = []
        current: int | None = start
        while current is not None and current in by_id:
            if current in seen:
                cycle = seen[seen.index(current):] + [current]
                if cycle not in cycles:
                    cycles.append(cycle)
                break
            seen.append(current)
            parent = by_id[current].get("parent_id")
            current = int(parent) if parent is not None else None

    orphan_references: dict[str, int] = {}
    inactive_references: dict[str, int] = {}
    stale_paths: dict[str, int] = {}
    paths = {int(row["id"]): row.get("path") for row in list_categories_v1(db, user)}
    text_columns = {
        "transactions": "category",
        "income_sources": "category",
        "recurring_expenses": "category",
        "bills": "bill_type",
        "planned_spending": "category",
        "budgets": "category_name",
    }
    for table in CATEGORY_REFERENCE_TABLES:
        orphan_references[table] = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {table} r
                    LEFT JOIN categories c ON c.id=r.category_id AND c.user_id=r.user_id
                    WHERE r.user_id=:uid AND r.category_id IS NOT NULL AND c.id IS NULL
                    """
                ),
                {"uid": user.id},
            ).scalar()
            or 0
        )
        inactive_references[table] = int(
            db.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {table} r
                    JOIN categories c ON c.id=r.category_id AND c.user_id=r.user_id
                    WHERE r.user_id=:uid AND r.category_id IS NOT NULL AND c.is_active=0
                    """
                ),
                {"uid": user.id},
            ).scalar()
            or 0
        )
        column = text_columns[table]
        stale = 0
        for record in db.execute(
            text(
                f"SELECT category_id,{column} AS value FROM {table} "
                "WHERE user_id=:uid AND category_id IS NOT NULL"
            ),
            {"uid": user.id},
        ).mappings().all():
            expected = paths.get(int(record["category_id"]))
            if (
                expected
                and record.get("value") not in (None, "")
                and str(record["value"]) != str(expected)
            ):
                stale += 1
        stale_paths[table] = stale

    type_conflicts = []
    for row in active:
        if row.get("parent_id") is None:
            continue
        parent = by_id.get(int(row["parent_id"]))
        if (
            parent
            and parent.get("category_type")
            and row.get("category_type")
            and parent["category_type"] != row["category_type"]
        ):
            type_conflicts.append(
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "category_type": row["category_type"],
                    "parent_id": int(parent["id"]),
                    "parent_type": parent["category_type"],
                }
            )

    issue_count = (
        len(duplicate_groups)
        + len(orphan_children)
        + len(inactive_parent_children)
        + len(cycles)
        + len(type_conflicts)
        + sum(orphan_references.values())
        + sum(inactive_references.values())
        + sum(stale_paths.values())
    )
    return {
        "status": "ok" if issue_count == 0 else "attention",
        "issue_count": issue_count,
        "duplicate_groups": duplicate_groups,
        "orphan_children": orphan_children,
        "children_of_inactive_parents": inactive_parent_children,
        "cycles": cycles,
        "orphan_references": orphan_references,
        "inactive_references": inactive_references,
        "stale_paths": stale_paths,
        "category_type_conflicts": type_conflicts,
    }


def _commitment_key(item: dict[str, Any]) -> tuple[Any, ...]:
    recurring_id = item.get("recurring_expense_id")
    if recurring_id:
        return ("recurring", int(recurring_id), str(item.get("date") or ""))
    source_id = item.get("source_id") or item.get("id")
    if source_id is not None:
        return (str(item.get("kind") or ""), int(source_id), str(item.get("date") or ""))
    return (
        str(item.get("kind") or ""),
        normalise_category_name(item.get("name")),
        str(item.get("date") or ""),
        str(item.get("amount") or item.get("amount_cents") or ""),
    )


def dedupe_commitments(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer explicit Bills over generated recurring occurrences for one obligation."""
    ordered = sorted(items, key=lambda item: 0 if item.get("kind") == "bill" else 1)
    seen: set[tuple[Any, ...]] = set()
    result: list[dict[str, Any]] = []
    for item in ordered:
        key = _commitment_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: str(item.get("date") or ""))


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


@router.get("/categories/health")
def category_health_endpoint(db: DbSession = DB, current_user: User = USER):
    return category_health(db, current_user)


@router.post("/categories/merge/preview")
def category_merge_preview(
    payload: dict[str, Any],
    db: DbSession = DB,
    current_user: User = USER,
):
    source_id = int(payload.get("source_id") or 0)
    destination_id = int(payload.get("destination_id") or 0)
    source = _category_row(db, current_user, source_id)
    destination = _category_row(db, current_user, destination_id)
    if source_id == destination_id:
        raise HTTPException(status_code=400, detail="Source and destination categories must be different")
    return {
        "source": {"id": source_id, "name": source["name"]},
        "destination": {"id": destination_id, "name": destination["name"]},
        "will_reassign": _reference_counts(db, current_user, source_id),
        "source_will_be_archived": True,
    }


@router.post("/categories/merge")
def category_merge_endpoint(
    payload: dict[str, Any],
    db: DbSession = DB,
    current_user: User = USER,
):
    return merge_category(
        db,
        current_user,
        int(payload.get("source_id") or 0),
        int(payload.get("destination_id") or 0),
    )


@router.get("/recurring-expenses/duplicates")
def recurring_duplicates(db: DbSession = DB, current_user: User = USER):
    rows = [
        dict(row)
        for row in db.execute(
            text(
                """
                SELECT id,name,amount_cents,frequency,next_due_date,account_id,card_id,is_active
                FROM recurring_expenses
                WHERE user_id=:uid AND is_active=1
                ORDER BY id
                """
            ),
            {"uid": current_user.id},
        ).mappings().all()
    ]
    groups: list[dict[str, Any]] = []
    used: set[int] = set()
    for index, row in enumerate(rows):
        if int(row["id"]) in used:
            continue
        matches = [row]
        for other in rows[index + 1 :]:
            name_matches = normalise_category_name(row["name"]) == normalise_category_name(other["name"])
            same_amount = row.get("amount_cents") == other.get("amount_cents")
            same_frequency = row.get("frequency") == other.get("frequency")
            same_payment_source = (
                row.get("card_id") == other.get("card_id")
                and row.get("account_id") == other.get("account_id")
            )
            dates = (_as_date(row.get("next_due_date")), _as_date(other.get("next_due_date")))
            dates_close = all(dates) and abs((dates[0] - dates[1]).days) <= 7
            if (
                name_matches
                and same_amount
                and same_frequency
                and same_payment_source
                and (dates_close or dates[0] == dates[1])
            ):
                matches.append(other)
        if len(matches) > 1:
            ids = [int(item["id"]) for item in matches]
            used.update(ids)
            groups.append(
                {
                    "confidence": "high",
                    "reason": (
                        "Same normalised name, amount, frequency and payment source "
                        "with matching/near due dates"
                    ),
                    "records": matches,
                }
            )
    return {"count": len(groups), "groups": groups}


@router.get("/cards/integrity")
def card_integrity(db: DbSession = DB, current_user: User = USER):
    orphan = int(
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM cards c
                LEFT JOIN accounts a ON a.id=c.account_id AND a.user_id=c.user_id
                WHERE c.user_id=:uid AND a.id IS NULL
                """
            ),
            {"uid": current_user.id},
        ).scalar()
        or 0
    )
    archived_account_cards = int(
        db.execute(
            text(
                """
                SELECT COUNT(*) FROM cards c
                JOIN accounts a ON a.id=c.account_id AND a.user_id=c.user_id
                WHERE c.user_id=:uid AND c.is_active=1 AND a.archived_at IS NOT NULL
                """
            ),
            {"uid": current_user.id},
        ).scalar()
        or 0
    )
    return {
        "status": "ok" if not orphan and not archived_account_cards else "attention",
        "orphan_cards": orphan,
        "active_cards_on_archived_accounts": archived_account_cards,
    }


@router.get("/upcoming-commitments")
def upcoming_commitments(
    days: int = Query(30, ge=1, le=365),
    account_id: int | None = None,
    category_id: int | None = None,
    commitment_type: str | None = None,
    include_overdue: bool = False,
    db: DbSession = DB,
    current_user: User = USER,
):
    start = today_local()
    end = start + timedelta(days=days)
    scheduled = schedule_summary(db, current_user, start, end)
    items = [
        item
        for item in scheduled.get("events", [])
        if item.get("kind") in OUTGOING_KINDS
    ]
    if include_overdue:
        overdue = db.execute(
            text(
                """
                SELECT id,name,due_date,remaining_amount_cents,bill_type,account_id,
                       category_id,recurring_expense_id
                FROM bills
                WHERE user_id=:uid AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL
                  AND due_date IS NOT NULL AND due_date < :today
                """
            ),
            {"uid": current_user.id, "today": start},
        ).mappings().all()
        for row in overdue:
            items.append(
                {
                    "id": int(row["id"]),
                    "source_id": int(row["id"]),
                    "kind": "bill",
                    "name": row["name"],
                    "date": str(row["due_date"]),
                    "amount_cents": int(row["remaining_amount_cents"] or 0),
                    "category": row["bill_type"],
                    "account_id": row["account_id"],
                    "category_id": row["category_id"],
                    "recurring_expense_id": row["recurring_expense_id"],
                    "status": "overdue",
                }
            )
    if account_id is not None:
        items = [item for item in items if item.get("account_id") in (None, account_id)]
    if category_id is not None:
        items = [item for item in items if item.get("category_id") == category_id]
    if commitment_type:
        items = [item for item in items if item.get("kind") == commitment_type]
    items = dedupe_commitments(items)
    return {
        "range_days": days,
        "include_overdue": include_overdue,
        "count": len(items),
        "items": items,
    }
