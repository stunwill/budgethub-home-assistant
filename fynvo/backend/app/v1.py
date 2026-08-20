from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import re
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

PAYMENT_METHODS = {
    "manual_payment": "Manual Payment",
    "direct_debit": "Direct Debit",
    "automatic_card_payment": "Automatic Card Payment",
    "bpay": "BPAY",
    "bank_transfer": "Bank Transfer",
    "cash": "Cash",
    "other": "Other",
    "not_set": "Not Set",
}
AMOUNT_TYPES = {
    "fixed": "Fixed Amount",
    "variable_estimated": "Variable / Estimated",
}
FREQUENCY_LABELS = {
    "weekly": "Weekly",
    "fortnightly": "Fortnightly",
    "every_28_days": "Every 4 Weeks",
    "every_4_weeks": "Every 4 Weeks",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
    "yearly": "Annually",
    "custom": "Custom",
    "one_off": "One-off",
}
SUPPORTED_FREQUENCIES = set(FREQUENCY_LABELS)
CARD_TYPES = {"debit", "credit", "prepaid", "other"}

CATEGORY_SEED: dict[str, list[str]] = {
    "Housing": ["Mortgage", "Rent", "Council Rates", "Body Corporate", "Home Maintenance & Improvements", "Security"],
    "Utilities": ["Electricity", "Gas", "Water", "Internet", "Mobile Phone", "Home Phone"],
    "Groceries & Household": ["Groceries", "Cleaning Products", "Household Supplies"],
    "Transport": ["Fuel", "Vehicle Registration", "Vehicle Insurance", "Servicing & Repairs", "Tyres", "Parking", "Tolls", "Public Transport", "Taxi & Rideshare"],
    "Insurance": ["Home & Contents", "Health", "Life", "Income Protection", "Pet", "Other Insurance"],
    "Health & Medical": ["Doctor", "Dental", "Pharmacy", "Specialists", "Physio & Allied Health", "Optical", "Medical Equipment"],
    "Entertainment": ["Streaming", "Music", "Movies", "Gaming", "Events", "Hobbies"],
    "Dining & Takeaway": ["Restaurants", "Takeaway", "Cafes", "Alcohol"],
    "Personal": ["Clothing", "Hair & Beauty", "Personal Care"],
    "Children & Family": ["School", "Childcare", "School Activities", "Clothing", "Pocket Money", "Child Activities"],
    "Pets": ["Pet Food", "Veterinary", "Medication", "Grooming", "Registration"],
    "Finance": ["Loan Repayments", "Credit Card Fees", "Bank Fees", "Interest", "Accounting"],
    "Subscriptions & Memberships": ["Software", "Cloud Storage", "News & Media", "Gym", "Clubs", "Professional Memberships"],
    "Government & Taxes": ["Tax", "Licences", "Permits", "Fines", "Other Government"],
    "Travel": ["Accommodation", "Flights", "Car Hire", "Travel Insurance", "Holiday Spending"],
    "Gifts & Donations": ["Gifts", "Charity", "Celebrations"],
    "Education": ["Courses", "Books", "Software", "Training"],
    "Other": ["Miscellaneous", "Uncategorized"],
}

EXPENSE_TYPE_SEED = [
    ("Bill", "Electricity, water, council rates"),
    ("Subscription", "Netflix, Spotify, iCloud"),
    ("Insurance", "Car, home, health insurance"),
    ("Loan Repayment", "Mortgage, personal loan, car loan"),
    ("Membership", "Gym, clubs, professional memberships"),
    ("Service", "Cleaner, lawn care, pest control"),
    ("Fee", "Bank fees, school fees, account fees"),
    ("Tax / Government", "Registration, licences, levies"),
    ("Regular Purchase", "Medication, pet food, recurring household purchases"),
    ("Other", "Anything that doesn't fit"),
]


class RecurringExpenseCreateV1(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    amount: str | None = None
    frequency: str | None = None
    interval_count: int | None = None
    next_due_date: date | None = None
    payment_method: str = "not_set"
    account_id: int | None = None
    card_id: int | None = None
    category_id: int | None = None
    expense_type_id: int | None = None
    payee_merchant: str | None = Field(default=None, max_length=180)
    amount_type: str = "fixed"
    end_date: date | None = None
    reminder_days_before: int | None = Field(default=None, ge=0, le=365)
    notes: str | None = None
    is_active: bool = True

    direct_debit: bool | None = None
    source_account_text: str | None = Field(default=None, max_length=140)
    category: str | None = Field(default=None, max_length=180)
    expense_type: str | None = Field(default=None, max_length=120)
    owner_group: str | None = Field(default=None, max_length=80)
    variable_amount: bool | None = None
    aliases: str | None = None
    last_paid_date: date | None = None


def _has_column(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return any(row["name"] == column for row in rows)


def _add_column(connection, table: str, definition: str) -> None:
    column = definition.split()[0]
    if not _has_column(connection, table, column):
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))


def run_v1_migrations(engine: Engine) -> None:
    """Forward-only v1 migration. Existing rows and IDs are never recreated."""
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS expense_types (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(120) NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                archived_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                name VARCHAR(140) NOT NULL,
                card_type VARCHAR(40) NOT NULL DEFAULT 'debit',
                last_four VARCHAR(4) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                archived_at DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        _add_column(connection, "transactions", "category_id INTEGER REFERENCES categories(id)")
        _add_column(connection, "income_sources", "category_id INTEGER REFERENCES categories(id)")
        _add_column(connection, "recurring_expenses", "category_id INTEGER REFERENCES categories(id)")
        _add_column(connection, "recurring_expenses", "expense_type_id INTEGER REFERENCES expense_types(id)")
        _add_column(connection, "recurring_expenses", "payment_method VARCHAR(40) NOT NULL DEFAULT 'not_set'")
        _add_column(connection, "recurring_expenses", "card_id INTEGER REFERENCES cards(id)")
        _add_column(connection, "recurring_expenses", "payee_merchant VARCHAR(180)")
        _add_column(connection, "recurring_expenses", "amount_type VARCHAR(40) NOT NULL DEFAULT 'fixed'")
        _add_column(connection, "recurring_expenses", "end_date DATE")
        _add_column(connection, "recurring_expenses", "reminder_days_before INTEGER")
        _add_column(connection, "bills", "category_id INTEGER REFERENCES categories(id)")
        _add_column(connection, "planned_spending", "category_id INTEGER REFERENCES categories(id)")
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_expense_types_user_active ON expense_types(user_id, is_active, name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_cards_user_account ON cards(user_id, account_id, is_active)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_recurring_category_id ON recurring_expenses(user_id, category_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_recurring_expense_type_id ON recurring_expenses(user_id, expense_type_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_recurring_card_id ON recurring_expenses(user_id, card_id)"))
        connection.execute(text("""
            UPDATE recurring_expenses
            SET payment_method = CASE
                WHEN direct_debit = 1 AND account_id IS NOT NULL THEN 'direct_debit'
                ELSE 'not_set'
            END
            WHERE payment_method IS NULL OR payment_method = '' OR payment_method = 'not_set'
        """))
        connection.execute(text("""
            UPDATE recurring_expenses
            SET amount_type = CASE WHEN variable_amount = 1 THEN 'variable_estimated' ELSE 'fixed' END
            WHERE amount_type IS NULL OR amount_type = ''
        """))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (9)"))
        elif int(current) < 9:
            connection.execute(text("UPDATE schema_version SET version=9"))


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def _fetch_categories(db: DbSession, user: User) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text("SELECT * FROM categories WHERE user_id=:uid ORDER BY COALESCE(parent_id,id), name"), {"uid": user.id}).mappings().all()]


def _category_paths(rows: list[dict[str, Any]]) -> dict[int, str]:
    by_id = {int(row["id"]): row for row in rows}
    output: dict[int, str] = {}
    for row in rows:
        names = [row["name"]]
        seen = {int(row["id"])}
        parent_id = row.get("parent_id")
        while parent_id is not None and int(parent_id) in by_id and int(parent_id) not in seen:
            seen.add(int(parent_id))
            parent = by_id[int(parent_id)]
            names.insert(0, parent["name"])
            parent_id = parent.get("parent_id")
        output[int(row["id"])] = " → ".join(names)
    return output


def list_categories_v1(db: DbSession, user: User) -> list[dict]:
    rows = _fetch_categories(db, user)
    paths = _category_paths(rows)
    result = []
    for row in rows:
        item = dict(row)
        item["path"] = paths[int(row["id"])]
        item["is_active"] = bool(row.get("is_active"))
        result.append(item)
    return result


def _category_exists(db: DbSession, user: User, category_id: int | None) -> bool:
    if category_id is None:
        return True
    return bool(db.execute(text("SELECT id FROM categories WHERE id=:id AND user_id=:uid"), {"id": category_id, "uid": user.id}).scalar())


def _would_cycle(db: DbSession, user: User, category_id: int, parent_id: int | None) -> bool:
    seen = {category_id}
    current = parent_id
    while current:
        if current in seen:
            return True
        seen.add(current)
        current = db.execute(text("SELECT parent_id FROM categories WHERE id=:id AND user_id=:uid"), {"id": current, "uid": user.id}).scalar()
    return False


def create_category_v1(db: DbSession, user: User, payload: dict[str, Any]) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    parent_id = payload.get("parent_id")
    if parent_id in ("", 0, "0"):
        parent_id = None
    if parent_id is not None:
        parent_id = int(parent_id)
        if not _category_exists(db, user, parent_id):
            raise HTTPException(status_code=404, detail="Parent category not found")
    duplicate = db.execute(text("""
        SELECT id FROM categories
        WHERE user_id=:uid
          AND ((parent_id IS NULL AND :parent_id IS NULL) OR parent_id=:parent_id)
          AND lower(name)=lower(:name)
    """), {"uid": user.id, "parent_id": parent_id, "name": name}).scalar()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A category with this name already exists under that parent")
    now = utcnow()
    db.execute(text("""
        INSERT INTO categories(user_id,name,parent_id,icon,color,category_type,budget_relationship,is_active,notes,created_at,updated_at)
        VALUES(:uid,:name,:parent_id,:icon,:color,:category_type,:relationship,1,:notes,:now,:now)
    """), {"uid": user.id, "name": name, "parent_id": parent_id, "icon": payload.get("icon"), "color": payload.get("color"), "category_type": payload.get("category_type") or "expense", "relationship": payload.get("budget_relationship") or "independent", "notes": payload.get("notes"), "now": now})
    cid = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.commit()
    return next(row for row in list_categories_v1(db, user) if row["id"] == cid)


def update_category_v1(db: DbSession, user: User, category_id: int, payload: dict[str, Any]) -> dict:
    existing = db.execute(text("SELECT * FROM categories WHERE id=:id AND user_id=:uid"), {"id": category_id, "uid": user.id}).mappings().first()
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    parent_id = payload.get("parent_id", existing["parent_id"])
    if parent_id in ("", 0, "0"):
        parent_id = None
    if parent_id is not None:
        parent_id = int(parent_id)
        if not _category_exists(db, user, parent_id):
            raise HTTPException(status_code=404, detail="Parent category not found")
        if _would_cycle(db, user, category_id, parent_id):
            raise HTTPException(status_code=400, detail="Category hierarchy cannot contain cycles")
    name = (payload.get("name", existing["name"]) or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Category name is required")
    relationship = payload.get("budget_relationship", existing["budget_relationship"] or "independent")
    if relationship not in {"independent", "shared_parent_pool", "sum_of_children"}:
        raise HTTPException(status_code=400, detail="Invalid budget relationship")
    duplicate = db.execute(text("""
        SELECT id FROM categories
        WHERE user_id=:uid AND id<>:id
          AND ((parent_id IS NULL AND :parent_id IS NULL) OR parent_id=:parent_id)
          AND lower(name)=lower(:name)
    """), {"uid": user.id, "id": category_id, "parent_id": parent_id, "name": name}).scalar()
    if duplicate:
        raise HTTPException(status_code=409, detail="A category with this name already exists under that parent")
    db.execute(text("""
        UPDATE categories
        SET name=:name,parent_id=:parent_id,icon=:icon,color=:color,category_type=:category_type,
            budget_relationship=:relationship,is_active=:active,notes=:notes,updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"id": category_id, "uid": user.id, "name": name, "parent_id": parent_id, "icon": payload.get("icon", existing["icon"]), "color": payload.get("color", existing["color"]), "category_type": payload.get("category_type", existing["category_type"]), "relationship": relationship, "active": bool(payload.get("is_active", existing["is_active"])), "notes": payload.get("notes", existing["notes"]), "now": utcnow()})
    _sync_category_denormalized_values(db, user)
    db.commit()
    return next(row for row in list_categories_v1(db, user) if row["id"] == category_id)


def _find_category_for_legacy_value(db: DbSession, user: User, value: str | None) -> int | None:
    needle = _norm((value or "").replace(">", "→"))
    if not needle:
        return None
    rows = list_categories_v1(db, user)
    exact_path = [row for row in rows if _norm(row["path"]) == needle]
    if len(exact_path) == 1:
        return int(exact_path[0]["id"])
    by_name = [row for row in rows if _norm(row["name"]) == needle]
    return int(by_name[0]["id"]) if len(by_name) == 1 else None


def _sync_category_denormalized_values(db: DbSession, user: User) -> None:
    rows = list_categories_v1(db, user)
    for item in rows:
        cid = int(item["id"])
        path = item["path"]
        for table in ("transactions", "income_sources", "recurring_expenses", "planned_spending"):
            if _has_column(db.connection(), table, "category_id"):
                db.execute(text(f"UPDATE {table} SET category=:path WHERE user_id=:uid AND category_id=:cid"), {"path": path, "uid": user.id, "cid": cid})
        if _has_column(db.connection(), "bills", "category_id"):
            db.execute(text("UPDATE bills SET bill_type=:path WHERE user_id=:uid AND category_id=:cid"), {"path": path, "uid": user.id, "cid": cid})
        db.execute(text("UPDATE budgets SET category_name=:path WHERE user_id=:uid AND category_id=:cid"), {"path": path, "uid": user.id, "cid": cid})


def ensure_reference_data(db: DbSession, user: User) -> None:
    now = utcnow()
    existing = _fetch_categories(db, user)
    roots = {_norm(row["name"]): int(row["id"]) for row in existing if row.get("parent_id") is None}
    for parent_name, children in CATEGORY_SEED.items():
        parent_id = roots.get(_norm(parent_name))
        if parent_id is None:
            db.execute(text("""
                INSERT INTO categories(user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at)
                VALUES(:uid,:name,NULL,'expense','independent',1,:now,:now)
            """), {"uid": user.id, "name": parent_name, "now": now})
            parent_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
            roots[_norm(parent_name)] = parent_id
        current_children = {_norm(row["name"]) for row in _fetch_categories(db, user) if row.get("parent_id") == parent_id}
        for child in children:
            if _norm(child) in current_children:
                continue
            db.execute(text("""
                INSERT INTO categories(user_id,name,parent_id,category_type,budget_relationship,is_active,created_at,updated_at)
                VALUES(:uid,:name,:parent_id,'expense','independent',1,:now,:now)
            """), {"uid": user.id, "name": child, "parent_id": parent_id, "now": now})

    existing_types = {_norm(row.name): row.id for row in db.execute(text("SELECT id,name FROM expense_types WHERE user_id=:uid"), {"uid": user.id}).all()}
    for name, description in EXPENSE_TYPE_SEED:
        if _norm(name) in existing_types:
            continue
        db.execute(text("INSERT INTO expense_types(user_id,name,description,is_active,created_at,updated_at) VALUES(:uid,:name,:description,1,:now,:now)"), {"uid": user.id, "name": name, "description": description, "now": now})
    db.flush()
    for table, value_column in (("transactions", "category"), ("income_sources", "category"), ("recurring_expenses", "category"), ("planned_spending", "category")):
        rows = db.execute(text(f"SELECT id,{value_column} AS value FROM {table} WHERE user_id=:uid AND category_id IS NULL AND {value_column} IS NOT NULL"), {"uid": user.id}).mappings().all()
        for row in rows:
            cid = _find_category_for_legacy_value(db, user, row["value"])
            if cid:
                db.execute(text(f"UPDATE {table} SET category_id=:cid WHERE id=:id AND user_id=:uid"), {"cid": cid, "id": row["id"], "uid": user.id})
    type_by_name = {_norm(row.name): int(row.id) for row in db.execute(text("SELECT id,name FROM expense_types WHERE user_id=:uid"), {"uid": user.id}).all()}
    for row in db.execute(text("SELECT id,expense_type FROM recurring_expenses WHERE user_id=:uid AND expense_type_id IS NULL AND expense_type IS NOT NULL"), {"uid": user.id}).mappings().all():
        etid = type_by_name.get(_norm(row["expense_type"]))
        if etid:
            db.execute(text("UPDATE recurring_expenses SET expense_type_id=:etid WHERE id=:id AND user_id=:uid"), {"etid": etid, "id": row["id"], "uid": user.id})
    _sync_category_denormalized_values(db, user)
    db.commit()


def list_expense_types(db: DbSession, user: User, include_inactive: bool = True) -> list[dict]:
    ensure_reference_data(db, user)
    sql = "SELECT * FROM expense_types WHERE user_id=:uid"
    if not include_inactive:
        sql += " AND is_active=1"
    sql += " ORDER BY is_active DESC,name"
    return [{**dict(row), "is_active": bool(row["is_active"])} for row in db.execute(text(sql), {"uid": user.id}).mappings().all()]


@router.get("/expense-types")
def expense_types(include_inactive: bool = True, current_user: User = USER, db: DbSession = DB):
    return list_expense_types(db, current_user, include_inactive)


@router.post("/expense-types", status_code=status.HTTP_201_CREATED)
def create_expense_type(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Expense Type name is required")
    ensure_reference_data(db, current_user)
    if db.execute(text("SELECT id FROM expense_types WHERE user_id=:uid AND lower(name)=lower(:name)"), {"uid": current_user.id, "name": name}).scalar():
        raise HTTPException(status_code=409, detail="Expense Type already exists")
    now = utcnow()
    db.execute(text("INSERT INTO expense_types(user_id,name,description,is_active,created_at,updated_at) VALUES(:uid,:name,:description,1,:now,:now)"), {"uid": current_user.id, "name": name, "description": payload.get("description"), "now": now})
    eid = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.commit()
    return next(row for row in list_expense_types(db, current_user) if row["id"] == eid)


@router.put("/expense-types/{expense_type_id}")
def update_expense_type(expense_type_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    row = db.execute(text("SELECT * FROM expense_types WHERE id=:id AND user_id=:uid"), {"id": expense_type_id, "uid": current_user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Expense Type not found")
    name = (payload.get("name", row["name"]) or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Expense Type name is required")
    duplicate = db.execute(text("SELECT id FROM expense_types WHERE user_id=:uid AND id<>:id AND lower(name)=lower(:name)"), {"uid": current_user.id, "id": expense_type_id, "name": name}).scalar()
    if duplicate:
        raise HTTPException(status_code=409, detail="Expense Type already exists")
    db.execute(text("""
        UPDATE expense_types SET name=:name,description=:description,is_active=:active,archived_at=:archived,updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"id": expense_type_id, "uid": current_user.id, "name": name, "description": payload.get("description", row["description"]), "active": bool(payload.get("is_active", row["is_active"])), "archived": None if bool(payload.get("is_active", row["is_active"])) else (row["archived_at"] or utcnow()), "now": utcnow()})
    db.execute(text("UPDATE recurring_expenses SET expense_type=:name WHERE user_id=:uid AND expense_type_id=:id"), {"name": name, "uid": current_user.id, "id": expense_type_id})
    db.commit()
    return next(row for row in list_expense_types(db, current_user) if row["id"] == expense_type_id)


def _card_response(row) -> dict:
    return {"id": row.id, "account_id": row.account_id, "account_name": row.account_name, "name": row.name, "card_type": row.card_type, "last_four": row.last_four, "display_name": f"{row.name} ••••{row.last_four}", "is_active": bool(row.is_active), "created_at": str(row.created_at), "updated_at": str(row.updated_at)}


def list_cards(db: DbSession, user: User, include_inactive: bool = False) -> list[dict]:
    sql = "SELECT c.*,a.name AS account_name FROM cards c JOIN accounts a ON a.id=c.account_id WHERE c.user_id=:uid"
    if not include_inactive:
        sql += " AND c.is_active=1 AND a.is_active=1"
    sql += " ORDER BY c.is_active DESC,a.name,c.name"
    return [_card_response(row) for row in db.execute(text(sql), {"uid": user.id}).all()]


def _validate_card(db: DbSession, user: User, payload: dict[str, Any], existing=None) -> tuple[int, str, str, str, bool]:
    account_id = int(payload.get("account_id", existing.account_id if existing else 0) or 0)
    account = db.execute(text("SELECT id,is_active FROM accounts WHERE id=:id AND user_id=:uid"), {"id": account_id, "uid": user.id}).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    name = (payload.get("name", existing.name if existing else "") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Card name is required")
    card_type = (payload.get("card_type", existing.card_type if existing else "debit") or "debit").lower()
    if card_type not in CARD_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported Card type")
    last_four = str(payload.get("last_four", existing.last_four if existing else "") or "").strip()
    if not re.fullmatch(r"\d{4}", last_four):
        raise HTTPException(status_code=400, detail="Last four digits must contain exactly 4 numbers")
    active = bool(payload.get("is_active", existing.is_active if existing else True))
    if active and not bool(account.is_active):
        raise HTTPException(status_code=409, detail="Active Cards must be linked to an active Account")
    return account_id, name, card_type, last_four, active


@router.get("/cards")
def cards(include_inactive: bool = False, current_user: User = USER, db: DbSession = DB):
    return list_cards(db, current_user, include_inactive)


@router.post("/cards", status_code=status.HTTP_201_CREATED)
def create_card(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    account_id, name, card_type, last_four, active = _validate_card(db, current_user, payload)
    now = utcnow()
    db.execute(text("INSERT INTO cards(user_id,account_id,name,card_type,last_four,is_active,created_at,updated_at) VALUES(:uid,:account_id,:name,:card_type,:last_four,:active,:now,:now)"), {"uid": current_user.id, "account_id": account_id, "name": name, "card_type": card_type, "last_four": last_four, "active": active, "now": now})
    cid = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.commit()
    return next(row for row in list_cards(db, current_user, True) if row["id"] == cid)


@router.put("/cards/{card_id}")
def update_card(card_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    existing = db.execute(text("SELECT * FROM cards WHERE id=:id AND user_id=:uid"), {"id": card_id, "uid": current_user.id}).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Card not found")
    account_id, name, card_type, last_four, active = _validate_card(db, current_user, payload, existing)
    db.execute(text("""
        UPDATE cards SET account_id=:account_id,name=:name,card_type=:card_type,last_four=:last_four,is_active=:active,archived_at=:archived,updated_at=:now
        WHERE id=:id AND user_id=:uid
    """), {"id": card_id, "uid": current_user.id, "account_id": account_id, "name": name, "card_type": card_type, "last_four": last_four, "active": active, "archived": None if active else (existing.archived_at or utcnow()), "now": utcnow()})
    db.commit()
    return next(row for row in list_cards(db, current_user, True) if row["id"] == card_id)


def _get_category(db: DbSession, user: User, category_id: int | None, active_only: bool = False) -> dict | None:
    if category_id is None:
        return None
    rows = list_categories_v1(db, user)
    row = next((item for item in rows if int(item["id"]) == int(category_id)), None)
    if not row:
        raise HTTPException(status_code=404, detail="Category not found")
    if active_only and not row["is_active"]:
        raise HTTPException(status_code=409, detail="Choose an active Category")
    return row


def _get_expense_type(db: DbSession, user: User, expense_type_id: int | None, active_only: bool = False) -> dict | None:
    if expense_type_id is None:
        return None
    row = db.execute(text("SELECT * FROM expense_types WHERE id=:id AND user_id=:uid"), {"id": expense_type_id, "uid": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Expense Type not found")
    if active_only and not bool(row["is_active"]):
        raise HTTPException(status_code=409, detail="Choose an active Expense Type")
    return dict(row)


def _get_card(db: DbSession, user: User, card_id: int | None, active_only: bool = False):
    if card_id is None:
        return None
    row = db.execute(text("SELECT c.*,a.name AS account_name,a.is_active AS account_active FROM cards c JOIN accounts a ON a.id=c.account_id WHERE c.id=:id AND c.user_id=:uid"), {"id": card_id, "uid": user.id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")
    if active_only and (not bool(row.is_active) or not bool(row.account_active)):
        raise HTTPException(status_code=409, detail="Choose an active Card")
    return row


def _validate_account(db: DbSession, user: User, account_id: int | None, active_only: bool = False) -> None:
    if account_id is None:
        return
    row = db.execute(text("SELECT is_active FROM accounts WHERE id=:id AND user_id=:uid"), {"id": account_id, "uid": user.id}).first()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    if active_only and not bool(row.is_active):
        raise HTTPException(status_code=409, detail="Choose an active Account")


def _annual_factor(frequency: str | None, interval_count: int | None = None) -> Decimal | None:
    return {"weekly": Decimal(52), "fortnightly": Decimal(26), "every_28_days": Decimal(13), "every_4_weeks": Decimal(13), "monthly": Decimal(12), "quarterly": Decimal(4), "yearly": Decimal(1)}.get(frequency) if frequency != "custom" else Decimal(365) / Decimal(max(interval_count or 1, 1))


def recurring_cost(amount_cents: int | None, frequency: str | None, interval_count: int | None = None) -> dict:
    if amount_cents is None or frequency in (None, "one_off"):
        return {"weekly": None, "monthly": None, "annual": cents_to_decimal(amount_cents) if amount_cents is not None else None}
    annual_factor = _annual_factor(frequency, interval_count)
    if annual_factor is None:
        return {"weekly": None, "monthly": None, "annual": None}
    annual = int((Decimal(amount_cents) * annual_factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return {"weekly": cents_to_decimal(round(annual / 52)), "monthly": cents_to_decimal(round(annual / 12)), "annual": cents_to_decimal(annual)}


def _recurring_response(db: DbSession, user: User, row) -> dict:
    category = _get_category(db, user, getattr(row, "category_id", None)) if getattr(row, "category_id", None) else None
    expense_type = _get_expense_type(db, user, getattr(row, "expense_type_id", None)) if getattr(row, "expense_type_id", None) else None
    card = _get_card(db, user, getattr(row, "card_id", None)) if getattr(row, "card_id", None) else None
    account = db.execute(text("SELECT name FROM accounts WHERE id=:id AND user_id=:uid"), {"id": row.account_id, "uid": user.id}).first() if row.account_id else None
    amount = cents_to_decimal(row.amount_cents) if row.amount_cents is not None else None
    payment_method = getattr(row, "payment_method", None) or ("direct_debit" if row.direct_debit else "not_set")
    amount_type = getattr(row, "amount_type", None) or ("variable_estimated" if row.variable_amount else "fixed")
    completeness = []
    if row.amount_cents is None: completeness.append("amount")
    if not row.frequency: completeness.append("frequency")
    if not row.next_due_date: completeness.append("next_due_date")
    if payment_method == "direct_debit" and not row.account_id: completeness.append("account")
    if payment_method == "automatic_card_payment" and not getattr(row, "card_id", None): completeness.append("card")
    if not getattr(row, "category_id", None): completeness.append("category")
    if not getattr(row, "expense_type_id", None): completeness.append("expense_type")
    status_name = "complete" if not completeness else f"incomplete: {', '.join(completeness)}"
    if not bool(row.is_active): status_name = "inactive"
    cost = recurring_cost(row.amount_cents, row.frequency, row.interval_count)
    return {"id": row.id, "name": row.name, "amount": amount, "frequency": row.frequency, "interval_count": row.interval_count, "next_due_date": row.next_due_date, "payment_method": payment_method, "payment_method_label": PAYMENT_METHODS.get(payment_method, payment_method.replace("_", " ").title()), "account_id": row.account_id, "account_name": account.name if account else None, "card_id": getattr(row, "card_id", None), "card_name": card.display_name if card else None, "linked_account_name": card.account_name if card else None, "category_id": getattr(row, "category_id", None), "category": category["path"] if category else row.category, "expense_type_id": getattr(row, "expense_type_id", None), "expense_type": expense_type["name"] if expense_type else row.expense_type, "payee_merchant": getattr(row, "payee_merchant", None), "amount_type": amount_type, "amount_type_label": AMOUNT_TYPES.get(amount_type, amount_type.replace("_", " ").title()), "end_date": getattr(row, "end_date", None), "reminder_days_before": getattr(row, "reminder_days_before", None), "is_active": bool(row.is_active), "notes": row.notes, "completeness": status_name, "missing_fields": completeness, "weekly_cost": cost["weekly"], "monthly_cost": cost["monthly"], "annual_cost": cost["annual"], "created_at": str(row.created_at), "updated_at": str(row.updated_at)}


def recurring_response(row) -> dict:
    amount = cents_to_decimal(row.amount_cents) if row.amount_cents is not None else None
    return {"id": row.id, "name": row.name, "amount": amount, "frequency": row.frequency, "interval_count": row.interval_count, "next_due_date": row.next_due_date, "direct_debit": bool(row.direct_debit), "account_id": row.account_id, "source_account": row.source_account_text, "category": row.category, "expense_type": row.expense_type, "owner_group": row.owner_group, "is_active": bool(row.is_active), "variable_amount": bool(row.variable_amount), "aliases": row.aliases, "notes": row.notes, "last_paid_date": row.last_paid_date, "source": row.source, "completeness": "complete" if row.amount_cents is not None and row.frequency and row.next_due_date else "incomplete"}


def list_recurring_v1(db: DbSession, user: User, filter_value: str = "all") -> list[dict]:
    ensure_reference_data(db, user)
    rows = db.execute(text("SELECT * FROM recurring_expenses WHERE user_id=:uid ORDER BY is_active DESC,next_due_date IS NULL,next_due_date,name"), {"uid": user.id}).all()
    items = [_recurring_response(db, user, row) for row in rows]
    if filter_value == "active": return [item for item in items if item["is_active"]]
    if filter_value == "inactive": return [item for item in items if not item["is_active"]]
    if filter_value == "complete": return [item for item in items if item["completeness"] in {"complete", "inactive"}]
    if filter_value == "incomplete": return [item for item in items if "incomplete" in item["completeness"]]
    return items


def _resolve_recurring_links(db: DbSession, user: User, payload: RecurringExpenseCreateV1) -> dict[str, Any]:
    ensure_reference_data(db, user)
    frequency = payload.frequency
    if frequency and frequency not in SUPPORTED_FREQUENCIES: raise HTTPException(status_code=400, detail="Unsupported recurrence frequency")
    payment_method = payload.payment_method or "not_set"
    if payment_method == "not_set" and payload.direct_debit is True: payment_method = "direct_debit"
    if payment_method not in PAYMENT_METHODS: raise HTTPException(status_code=400, detail="Unsupported Payment Method")
    amount_type = payload.amount_type or ("variable_estimated" if payload.variable_amount else "fixed")
    if amount_type not in AMOUNT_TYPES: raise HTTPException(status_code=400, detail="Unsupported Amount Type")
    category = _get_category(db, user, payload.category_id, active_only=True) if payload.category_id else None
    if category is None and payload.category:
        cid = _find_category_for_legacy_value(db, user, payload.category); category = _get_category(db, user, cid) if cid else None
    expense_type = _get_expense_type(db, user, payload.expense_type_id, active_only=True) if payload.expense_type_id else None
    if expense_type is None and payload.expense_type:
        matches = [row for row in list_expense_types(db, user, False) if _norm(row["name"]) == _norm(payload.expense_type)]; expense_type = matches[0] if len(matches) == 1 else None
    account_id = payload.account_id; card_id = payload.card_id; card = None
    if payment_method == "direct_debit":
        if account_id is None: raise HTTPException(status_code=400, detail="Choose a Bank Account for Direct Debit")
        _validate_account(db, user, account_id, active_only=True); card_id = None
    elif payment_method == "automatic_card_payment":
        if card_id is None: raise HTTPException(status_code=400, detail="Choose a Card for Automatic Card Payment")
        card = _get_card(db, user, card_id, active_only=True); account_id = int(card.account_id)
    else:
        _validate_account(db, user, account_id, active_only=False); card_id = None
    if payload.end_date and payload.next_due_date and payload.end_date < payload.next_due_date: raise HTTPException(status_code=400, detail="End Date cannot be before Next Due")
    return {"payment_method": payment_method, "amount_type": amount_type, "category": category, "expense_type": expense_type, "account_id": account_id, "card_id": card_id, "card": card}


def create_recurring_v1(db: DbSession, user: User, payload: RecurringExpenseCreateV1) -> dict:
    links = _resolve_recurring_links(db, user, payload); now = utcnow(); amount_cents = parse_money(payload.amount) if payload.amount not in (None, "") else None; category = links["category"]; expense_type = links["expense_type"]
    db.execute(text("""
        INSERT INTO recurring_expenses(user_id,name,amount_cents,frequency,interval_count,next_due_date,direct_debit,account_id,source_account_text,category,category_id,expense_type,expense_type_id,owner_group,is_active,variable_amount,aliases,notes,last_paid_date,payment_method,card_id,payee_merchant,amount_type,end_date,reminder_days_before,source,created_at,updated_at)
        VALUES(:uid,:name,:amount,:frequency,:interval,:next_due,:direct_debit,:account_id,:source_account,:category,:category_id,:expense_type,:expense_type_id,:owner_group,:active,:variable,:aliases,:notes,:last_paid,:payment_method,:card_id,:payee,:amount_type,:end_date,:reminder,'manual',:now,:now)
    """), {"uid": user.id, "name": payload.name.strip(), "amount": amount_cents, "frequency": payload.frequency, "interval": payload.interval_count, "next_due": payload.next_due_date, "direct_debit": links["payment_method"] == "direct_debit", "account_id": links["account_id"], "source_account": payload.source_account_text, "category": category["path"] if category else payload.category, "category_id": category["id"] if category else None, "expense_type": expense_type["name"] if expense_type else payload.expense_type, "expense_type_id": expense_type["id"] if expense_type else None, "owner_group": payload.owner_group, "active": payload.is_active, "variable": links["amount_type"] == "variable_estimated", "aliases": payload.aliases, "notes": payload.notes, "last_paid": payload.last_paid_date, "payment_method": links["payment_method"], "card_id": links["card_id"], "payee": payload.payee_merchant, "amount_type": links["amount_type"], "end_date": payload.end_date, "reminder": payload.reminder_days_before, "now": now})
    rid = int(db.execute(text("SELECT last_insert_rowid()")).scalar()); db.commit(); row = db.execute(text("SELECT * FROM recurring_expenses WHERE id=:id AND user_id=:uid"), {"id": rid, "uid": user.id}).first(); return _recurring_response(db, user, row)


@router.put("/recurring-expenses/{expense_id}")
def update_recurring_v1(expense_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    existing = db.execute(text("SELECT * FROM recurring_expenses WHERE id=:id AND user_id=:uid"), {"id": expense_id, "uid": current_user.id}).mappings().first()
    if not existing: raise HTTPException(status_code=404, detail="Recurring Expense not found")
    merged = dict(existing); merged.update({k: v for k, v in payload.items() if v is not None}); merged["amount"] = cents_to_decimal(existing["amount_cents"]) if existing["amount_cents"] is not None else None
    if "amount" in payload: merged["amount"] = payload["amount"]
    request = RecurringExpenseCreateV1(**{key: merged.get(key) for key in RecurringExpenseCreateV1.model_fields if key in merged}); links = _resolve_recurring_links(db, current_user, request)
    effective_from = payload.get("effective_from"); amount_update = payload.get("amount") if "amount" in payload else None
    values = {"id": expense_id, "uid": current_user.id, "name": request.name.strip(), "frequency": request.frequency, "interval": request.interval_count, "next_due": request.next_due_date, "direct_debit": links["payment_method"] == "direct_debit", "account_id": links["account_id"], "source_account": request.source_account_text, "category": links["category"]["path"] if links["category"] else request.category, "category_id": links["category"]["id"] if links["category"] else None, "expense_type": links["expense_type"]["name"] if links["expense_type"] else request.expense_type, "expense_type_id": links["expense_type"]["id"] if links["expense_type"] else None, "owner_group": request.owner_group, "active": request.is_active, "variable": links["amount_type"] == "variable_estimated", "aliases": request.aliases, "notes": request.notes, "last_paid": request.last_paid_date, "payment_method": links["payment_method"], "card_id": links["card_id"], "payee": request.payee_merchant, "amount_type": links["amount_type"], "end_date": request.end_date, "reminder": request.reminder_days_before, "now": utcnow()}
    db.execute(text("""
        UPDATE recurring_expenses SET name=:name,frequency=:frequency,interval_count=:interval,next_due_date=:next_due,direct_debit=:direct_debit,account_id=:account_id,source_account_text=:source_account,category=:category,category_id=:category_id,expense_type=:expense_type,expense_type_id=:expense_type_id,owner_group=:owner_group,is_active=:active,variable_amount=:variable,aliases=:aliases,notes=:notes,last_paid_date=:last_paid,payment_method=:payment_method,card_id=:card_id,payee_merchant=:payee,amount_type=:amount_type,end_date=:end_date,reminder_days_before=:reminder,updated_at=:now WHERE id=:id AND user_id=:uid
    """), values)
    if "amount" in payload:
        new_amount = parse_money(amount_update) if amount_update not in (None, "") else None
        if effective_from and new_amount is not None:
            effective_date = date.fromisoformat(str(effective_from)[:10]); db.execute(text("INSERT INTO effective_amount_changes(user_id,record_type,record_id,new_amount_cents,effective_from,source,notes,created_at,updated_at) VALUES(:uid,'recurring_expense',:id,:amount,:effective_from,'edit',:notes,:now,:now)"), {"uid": current_user.id, "id": expense_id, "amount": new_amount, "effective_from": effective_date, "notes": payload.get("edit_mode") or "Change going forward", "now": utcnow()})
        else:
            db.execute(text("UPDATE recurring_expenses SET amount_cents=:amount WHERE id=:id AND user_id=:uid"), {"amount": new_amount, "id": expense_id, "uid": current_user.id})
    db.commit(); row = db.execute(text("SELECT * FROM recurring_expenses WHERE id=:id AND user_id=:uid"), {"id": expense_id, "uid": current_user.id}).first(); return _recurring_response(db, current_user, row)


@router.get("/recurring-expenses/meta")
def recurring_meta(current_user: User = USER, db: DbSession = DB):
    ensure_reference_data(db, current_user)
    return {"payment_methods": [{"value": key, "label": label} for key, label in PAYMENT_METHODS.items()], "amount_types": [{"value": key, "label": label} for key, label in AMOUNT_TYPES.items()], "frequencies": [{"value": key, "label": label} for key, label in FREQUENCY_LABELS.items()], "categories": [row for row in list_categories_v1(db, current_user) if row["is_active"]], "expense_types": list_expense_types(db, current_user, False), "cards": list_cards(db, current_user, False)}


@router.get("/recurring-expenses/cost")
def recurring_cost_endpoint(amount: str, frequency: str, interval_count: int | None = None, current_user: User = USER):
    if frequency not in SUPPORTED_FREQUENCIES: raise HTTPException(status_code=400, detail="Unsupported recurrence frequency")
    return recurring_cost(parse_money(amount), frequency, interval_count)


@router.get("/reference-data")
def reference_data(current_user: User = USER, db: DbSession = DB):
    ensure_reference_data(db, current_user); return {"categories": list_categories_v1(db, current_user), "expense_types": list_expense_types(db, current_user)}


def _add_period(value: date, frequency: str | None, interval: int | None = None) -> date | None:
    if frequency in (None, "one_off"): return None
    if frequency == "weekly": return value + timedelta(days=7)
    if frequency == "fortnightly": return value + timedelta(days=14)
    if frequency in {"every_28_days", "every_4_weeks"}: return value + timedelta(days=28)
    if frequency == "custom": return value + timedelta(days=max(interval or 1, 1))
    months = 1 if frequency == "monthly" else 3 if frequency == "quarterly" else 12 if frequency == "yearly" else 1
    month = value.month - 1 + months; year = value.year + month // 12; month = month % 12 + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def _as_date(value) -> date | None:
    if value in (None, ""): return None
    if isinstance(value, date): return value
    return date.fromisoformat(str(value)[:10])


def _effective_amount(db: DbSession, user: User, record_type: str, record_id: int, base: int | None, when: date) -> int | None:
    amount = base
    for change in db.execute(text("SELECT * FROM effective_amount_changes WHERE user_id=:uid AND record_type=:kind AND record_id=:rid AND effective_from<=:when AND (effective_to IS NULL OR effective_to>=:when) ORDER BY effective_from,id"), {"uid": user.id, "kind": record_type, "rid": record_id, "when": when}).mappings().all(): amount = int(change["new_amount_cents"])
    return amount


def _occurrence_dates(start_value, range_start: date, range_end: date, frequency: str | None, interval: int | None, end_date=None):
    current = _as_date(start_value); hard_end = min(range_end, _as_date(end_date)) if _as_date(end_date) else range_end
    if not current or current > hard_end: return
    while current < range_start and frequency != "one_off":
        nxt = _add_period(current, frequency, interval)
        if not nxt or nxt <= current: return
        current = nxt
    while current <= hard_end:
        if current >= range_start: yield current
        nxt = _add_period(current, frequency, interval)
        if not nxt: return
        current = nxt


def schedule_events_v1(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    ensure_reference_data(db, user); events: list[dict] = []
    linked_bills = {(int(row.recurring_expense_id), str(row.due_date)[:10]) for row in db.execute(text("SELECT recurring_expense_id,due_date FROM bills WHERE user_id=:uid AND is_active=1 AND recurring_expense_id IS NOT NULL AND due_date IS NOT NULL AND paid_at IS NULL AND resolved_at IS NULL"), {"uid": user.id}).all()}
    for row in db.execute(text("SELECT * FROM income_sources WHERE user_id=:uid AND is_active=1"), {"uid": user.id}).all():
        for when in _occurrence_dates(row.next_payment_date, start, end, row.frequency, row.interval_count, row.end_date):
            amount = _effective_amount(db, user, "income", row.id, row.amount_cents, when)
            if amount is not None: events.append({"date": when.isoformat(), "name": row.name, "amount_cents": amount, "amount": cents_to_decimal(amount), "kind": "income", "category": row.category or "Revenue / Income", "provider": row.payer, "source": "income"})
    for row in db.execute(text("SELECT * FROM recurring_expenses WHERE user_id=:uid AND is_active=1"), {"uid": user.id}).all():
        for when in _occurrence_dates(row.next_due_date, start, end, row.frequency, row.interval_count, getattr(row, "end_date", None)):
            if (int(row.id), when.isoformat()) in linked_bills: continue
            amount = _effective_amount(db, user, "recurring_expense", row.id, row.amount_cents, when)
            if amount is not None: events.append({"date": when.isoformat(), "name": row.name, "amount_cents": amount, "amount": cents_to_decimal(amount), "kind": "recurring_expense", "category": row.category or "Miscellaneous", "provider": getattr(row, "payee_merchant", None) or row.expense_type, "account": row.source_account_text, "source": "recurring_expense"})
    for row in db.execute(text("SELECT * FROM bills WHERE user_id=:uid AND is_active=1 AND paid_at IS NULL AND resolved_at IS NULL"), {"uid": user.id}).all():
        due = _as_date(row.due_date)
        if due and row.remaining_amount_cents is not None and start <= due <= end: events.append({"date": due.isoformat(), "name": row.name, "amount_cents": row.remaining_amount_cents, "amount": cents_to_decimal(row.remaining_amount_cents), "kind": "bill", "category": row.bill_type or "Financial Obligations", "provider": row.provider, "source": "bill"})
    for row in db.execute(text("SELECT * FROM planned_spending WHERE user_id=:uid AND include_in_forecast=1 AND archived_at IS NULL AND status IN ('planned','committed')"), {"uid": user.id}).all():
        when = _as_date(row.planned_date)
        if when and row.estimated_amount_cents is not None and start <= when <= end: events.append({"date": when.isoformat(), "name": row.name, "amount_cents": row.estimated_amount_cents, "amount": cents_to_decimal(row.estimated_amount_cents), "kind": "planned_spending", "category": row.category or "Planned Spending", "provider": row.merchant, "status": row.status, "priority": row.priority, "source": "planned_spending"})
    return sorted(events, key=lambda item: (item["date"], item["kind"], item["name"]))


def forecast_recurring_events_v1(db: DbSession, user: User, start: date, end: date, scenario: dict | None = None) -> list[dict]:
    from .forecast import _event
    scenario = scenario or {}; removed = set(scenario.get("remove_recurring_ids", [])); virtual_changes = scenario.get("amount_changes", {}); events = []
    linked_bills = {(int(row.recurring_expense_id), str(row.due_date)[:10]) for row in db.execute(text("SELECT recurring_expense_id,due_date FROM bills WHERE user_id=:uid AND is_active=1 AND recurring_expense_id IS NOT NULL AND due_date IS NOT NULL AND paid_at IS NULL AND resolved_at IS NULL"), {"uid": user.id}).all()}
    for record_type, table, date_col, account_col, direction, source_type in [("income", "income_sources", "next_payment_date", "destination_account_id", "income", "income"), ("recurring_expense", "recurring_expenses", "next_due_date", "account_id", "expense", "recurring_expense")]:
        rows = db.execute(text(f"SELECT * FROM {table} WHERE user_id=:uid AND is_active=1 AND {date_col} IS NOT NULL AND amount_cents IS NOT NULL"), {"uid": user.id}).mappings().all()
        for row in rows:
            if record_type == "recurring_expense" and int(row["id"]) in removed: continue
            for when in _occurrence_dates(row[date_col], start, end, row.get("frequency"), row.get("interval_count"), row.get("end_date")):
                if record_type == "recurring_expense" and (int(row["id"]), when.isoformat()) in linked_bills: continue
                amount = _effective_amount(db, user, record_type, int(row["id"]), row.get("amount_cents"), when); amount = virtual_changes.get(f"{record_type}:{row['id']}:{when.isoformat()}", amount)
                if amount is None: continue
                explanation = "Recurring income" if direction == "income" else "Recurring expense"
                events.append(_event(when, row["name"], int(amount), direction, source_type, int(row["id"]), row.get("category"), row.get(account_col), "confirmed", "committed", explanation))
    return events
