from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .models import Account, User
from .money import cents_to_decimal, parse_money
from .security import utcnow

FREQUENCIES = {"weekly", "fortnightly", "every_28_days", "every_4_weeks", "monthly", "quarterly", "yearly", "custom", "one_off"}
BILL_PRIORITIES = {"high", "normal", "low"}

RECURRING_SEED = [
    ("Home Loan", "2802.00", "monthly", "2026-09-01", True, "KW ING Everyday", "Home", "Mortgage", True, False, None),
    ("Telstra", "120.00", "monthly", "2026-08-21", True, "KW ING Everyday", "Living", "Phone/Internet", True, False, None),
    ("Sienna's Savings", None, None, None, True, "KW ING Everyday", "Financial Obligations", "Savings Contribution", True, False, "Goal: Reach $20,000 by age 18"),
    ("Other Savings", None, None, None, True, "ING Everyday", "Financial Obligations", "Savings Contribution", True, False, "Goal: Save $7,000 by end of November for a holiday"),
    ("Kristy Car Insurance", "116.00", "monthly", "2026-08-21", True, "ING Everyday", "Transportation", "Insurance", True, False, None),
    ("Stuart Car Insurance", "133.00", "monthly", "2026-08-22", True, "ING Everyday", "Transportation", "Insurance", True, False, None),
    ("House & Contents Insurance", "250.00", "monthly", "2026-08-23", True, "ING Everyday", "Home", "Insurance", True, False, None),
    ("iCloud Storage", "4.49", "monthly", "2026-08-14", True, "KW ING Everyday", "Entertainment", "Subscription", True, False, None),
    ("MRCC", None, "yearly", None, False, "KW ING Everyday", "Home", "Rates", True, True, "Date unknown"),
    ("Powershop", None, "weekly", None, False, "KW ING Everyday", "Home", "Electricity", True, True, "Date unknown"),
    ("LMW", None, "quarterly", None, False, "KW ING Everyday", "Home", "Water", True, True, "Date unknown"),
    ("Origin", None, "monthly", None, False, "KW ING Everyday", "Home", "Gas", True, True, "Date unknown"),
    ("Ambulance", "120.00", "yearly", "2027-08-01", False, "KW ING Everyday", "Health", "Insurance", True, False, "Annual cover due 1 August"),
    ("Myosprt / Osteo Kristy", "100.00", "every_4_weeks", None, False, "KW ING Everyday", "Health", "Medical", True, False, "Next date unknown"),
    ("School Fees", "200.00", "yearly", None, False, "KW ING Everyday", "Recreation", "School", True, False, "January, exact date unknown"),
    ("Netflix", "30.00", "monthly", None, True, "KW ING Everyday", "Entertainment", "Subscription", True, False, "Date unknown"),
    ("Spotify", "28.00", "monthly", None, True, "KW ING Everyday", "Entertainment", "Subscription", True, False, "Date unknown"),
    ("Dance Fees", "1600.00", "yearly", None, False, "KW ING Everyday", "Recreation", "Dance", True, False, "Date unknown"),
    ("Kienetic", "120.00", "monthly", None, True, "KW ING Everyday", "Health", "Medical", False, False, "Inactive legacy recurring expense"),
    ("Disney", "21.00", "monthly", None, True, "KW ING Everyday", "Entertainment", "Subscription", False, False, "Inactive legacy recurring expense"),
]

BILL_SEED = [
    ("Water Bill", "LMW", "Water Bill", "high", "Overdue", None, "400", None, "2026-07-24", "Paid through 24 Jul 2026"),
    ("Electricity", "Powershop", "Electricity", "high", "Overdue", None, "237", None, "2026-07-27", "Paid through 27 Jul 2026"),
    ("Rates", "MRCC", "Rates", "high", "Overdue", None, None, None, None, "$5,685.13 owed to Pauline. Set up payment plan when Stu gets a job"),
    ("Plumber", "Robinsons", "Plumber", "low", "Overdue", "2025-06-30", "800", None, None, "One-off outstanding bill"),
    ("Pool Rego", "MRCC", "Pool Rego", "low", "Overdue", "2025-06-30", None, None, None, "Pay before summer once glass is fixed. Stuart to call 24.7"),
    ("Stuart Rego", "VicRoads", "Registration", "high", "Source says Not Due", "2026-08-28", "170", "2026-08-27", None, "One-off registration"),
    ("Kristy Phone", "Boost", "Phone", "high", "Source says Not Due", "2026-08-21", "28", "2026-08-13", None, "Every 28 days, not monthly"),
    ("Kristy Car Insurance", "Budget Direct", "Insurance", "high", "Source says Due Now", "2026-08-05", "116", "2026-07-30", None, "Kristy Everyday Account"),
    ("House & Contents", "Budget Direct", "Insurance", "high", "Source says Not Due", "2026-08-01", "75", "2026-07-30", None, "Payment"),
    ("House & Contents", "Budget Direct", "Insurance", "normal", "Source says Not Due", "2026-08-14", "75", "2026-08-13", None, "Payment"),
    ("Netflix", "Netflix", "Subscription", "high", "Source says Not Due", "2026-08-19", "29", "2026-08-13", None, "Recurring candidate"),
    ("Spotify", "Spotify", "Subscription", "high", "Source says Not Due", None, None, None, None, "Incomplete"),
    ("House Payment x2", None, "Mortgage", "high", "Overdue", "2026-07-01", "1300", "2026-07-30", None, "Outstanding/missed payment"),
    ("House Payment x1", "ING", "Mortgage", "high", "Source says Not Due", "2026-08-01", "1400", "2026-08-13", None, "Mortgage-related"),
    ("House Payment x2", None, "Mortgage", "high", "Source says Not Due", "2026-08-01", "1300", "2026-08-27", None, "Mortgage-related"),
    ("Stuart Car Insurance", "Budget Direct", "Insurance", "high", "Source says Not Due", "2026-08-25", "134", None, None, "Recurring candidate"),
    ("Stuart Phone", "Boost", "Phone", "high", "Source says Not Due", "2026-08-21", "28", "2026-08-13", None, "Every 28 days, not monthly"),
    ("Internet", None, "Internet", "high", "Source says Not Due", None, None, None, None, "Incomplete"),
]


def today_local() -> date:
    return utcnow().date()


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _c(value: str | None) -> int | None:
    return parse_money(value) if value not in (None, "") else None


def account_match(db: DbSession, user: User, text_value: str | None) -> int | None:
    if not text_value:
        return None
    normal = text_value.strip().lower()
    matches = [row for row in db.query(Account).filter(Account.user_id == user.id).all() if row.name.lower() == normal]
    return matches[0].id if len(matches) == 1 else None


def ensure_seed_data(db: DbSession, user: User) -> None:
    seeded = db.execute(text("SELECT value FROM app_config WHERE key = :key"), {"key": f"v0.4.seeded.{user.id}"}).scalar()
    if seeded:
        return
    now = utcnow()
    for name, amount, frequency, next_due, dd, source_account, category, typ, active, variable, notes in RECURRING_SEED:
        db.execute(
            text("""
                INSERT INTO recurring_expenses (user_id, name, amount_cents, frequency, next_due_date, direct_debit, account_id, source_account_text, category, expense_type, is_active, variable_amount, notes, source, created_at, updated_at)
                VALUES (:user_id, :name, :amount, :frequency, :next_due, :direct_debit, :account_id, :source_account, :category, :expense_type, :is_active, :variable_amount, :notes, 'seed', :now, :now)
            """),
            {
                "user_id": user.id,
                "name": name,
                "amount": _c(amount),
                "frequency": frequency,
                "next_due": _as_date(next_due),
                "direct_debit": dd,
                "account_id": account_match(db, user, source_account),
                "source_account": source_account,
                "category": category,
                "expense_type": typ,
                "is_active": active,
                "variable_amount": variable,
                "notes": notes,
                "now": now,
            },
        )
    db.flush()
    recurring = {row.name.lower(): row.id for row in db.execute(text("SELECT id, name FROM recurring_expenses WHERE user_id = :user_id"), {"user_id": user.id}).all()}
    for name, provider, typ, priority, original_status, due, amount, pay_cycle, paid_through, notes in BILL_SEED:
        link = recurring.get(name.lower()) or recurring.get((provider or "").lower())
        db.execute(
            text("""
                INSERT INTO bills (user_id, recurring_expense_id, name, provider, bill_type, priority, original_status, original_amount_cents, remaining_amount_cents, due_date, pay_cycle_date, paid_through_date, notes, is_active, source, created_at, updated_at)
                VALUES (:user_id, :recurring_id, :name, :provider, :bill_type, :priority, :original_status, :amount, :amount, :due_date, :pay_cycle_date, :paid_through_date, :notes, 1, 'seed', :now, :now)
            """),
            {
                "user_id": user.id,
                "recurring_id": link,
                "name": name,
                "provider": provider,
                "bill_type": typ,
                "priority": priority,
                "original_status": original_status,
                "amount": _c(amount),
                "due_date": _as_date(due),
                "pay_cycle_date": _as_date(pay_cycle),
                "paid_through_date": _as_date(paid_through),
                "notes": notes,
                "now": now,
            },
        )
    db.execute(text("INSERT INTO app_config (key, value, updated_at) VALUES (:key, 'true', :now)"), {"key": f"v0.4.seeded.{user.id}", "now": now})
    db.commit()


def completeness(amount: int | None, frequency: str | None, when, account_id: int | None, active: bool = True) -> tuple[str, list[str]]:
    missing = []
    if amount is None:
        missing.append("amount")
    if not frequency:
        missing.append("frequency")
    if not _as_date(when):
        missing.append("next date")
    if account_id is None:
        missing.append("account link")
    if not missing and active:
        return "complete", missing
    if not missing:
        return "inactive", missing
    return ("incomplete" if active else "inactive_incomplete"), missing


def bill_status(due, paid_at, resolved_at, remaining: int | None, original_status: str | None = None, today: date | None = None) -> str:
    due_date = _as_date(due)
    current_day = today or today_local()
    if paid_at or resolved_at or remaining == 0:
        return "paid"
    if due_date is None:
        if remaining is not None and original_status and "overdue" in original_status.lower():
            return "overdue"
        return "unknown"
    if due_date < current_day:
        return "overdue"
    if due_date == current_day:
        return "due_today"
    if due_date <= current_day + timedelta(days=7):
        return "due_soon"
    return "upcoming"


def add_period(value: date, frequency: str | None, interval: int | None = None) -> date | None:
    if frequency in (None, "one_off"):
        return None
    if frequency == "weekly":
        return value + timedelta(days=7)
    if frequency == "fortnightly":
        return value + timedelta(days=14)
    if frequency in {"every_28_days", "every_4_weeks"}:
        return value + timedelta(days=28)
    if frequency == "custom":
        return value + timedelta(days=max(interval or 1, 1))
    months = 1 if frequency == "monthly" else 3 if frequency == "quarterly" else 12 if frequency == "yearly" else 1
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def occurrences(start, end: date, amount: int | None, frequency: str | None, name: str, kind: str, meta: dict, interval: int | None = None) -> list[dict]:
    current = _as_date(start)
    if not current or amount is None:
        return []
    while current < today_local() - timedelta(days=370) and frequency != "one_off":
        nxt = add_period(current, frequency, interval)
        if not nxt or nxt <= current:
            break
        current = nxt
    rows = []
    while current <= end:
        if current >= meta.get("range_start", current):
            rows.append({"date": current.isoformat(), "name": name, "amount_cents": amount, "amount": cents_to_decimal(amount), "kind": kind, **meta})
        nxt = add_period(current, frequency, interval)
        if not nxt:
            break
        current = nxt
    return rows


def recurring_response(row) -> dict:
    next_due = _as_date(row.next_due_date)
    state, missing = completeness(row.amount_cents, row.frequency, next_due, row.account_id, bool(row.is_active))
    return {
        "id": row.id,
        "name": row.name,
        "amount": cents_to_decimal(row.amount_cents) if row.amount_cents is not None else None,
        "frequency": row.frequency,
        "next_due_date": next_due.isoformat() if next_due else None,
        "direct_debit": row.direct_debit,
        "account_id": row.account_id,
        "source_account_text": row.source_account_text,
        "category": row.category,
        "expense_type": row.expense_type,
        "owner_group": row.owner_group,
        "is_active": bool(row.is_active),
        "variable_amount": bool(row.variable_amount),
        "notes": row.notes,
        "completeness": state,
        "missing_fields": missing,
    }


def bill_response(row, today: date | None = None) -> dict:
    due_date = _as_date(row.due_date)
    current_day = today or today_local()
    status_value = bill_status(due_date, row.paid_at, row.resolved_at, row.remaining_amount_cents, row.original_status, current_day)
    days_overdue = (current_day - due_date).days if due_date and status_value == "overdue" else None
    return {
        "id": row.id,
        "recurring_expense_id": row.recurring_expense_id,
        "name": row.name,
        "provider": row.provider,
        "bill_type": row.bill_type,
        "priority": row.priority,
        "original_status": row.original_status,
        "amount": cents_to_decimal(row.remaining_amount_cents) if row.remaining_amount_cents is not None else None,
        "due_date": due_date.isoformat() if due_date else None,
        "pay_cycle_date": _as_date(row.pay_cycle_date).isoformat() if _as_date(row.pay_cycle_date) else None,
        "paid_through_date": _as_date(row.paid_through_date).isoformat() if _as_date(row.paid_through_date) else None,
        "notes": row.notes,
        "status": status_value,
        "days_overdue": days_overdue,
    }


def income_response(row) -> dict:
    next_payment = _as_date(row.next_payment_date)
    state, missing = completeness(row.amount_cents, row.frequency, next_payment, row.destination_account_id, bool(row.is_active))
    return {
        "id": row.id,
        "name": row.name,
        "amount": cents_to_decimal(row.amount_cents) if row.amount_cents is not None else None,
        "frequency": row.frequency,
        "next_payment_date": next_payment.isoformat() if next_payment else None,
        "destination_account_id": row.destination_account_id,
        "payer": row.payer,
        "category": row.category,
        "is_active": bool(row.is_active),
        "notes": row.notes,
        "completeness": state,
        "missing_fields": missing,
    }


def list_income(db: DbSession, user: User) -> list[dict]:
    rows = db.execute(text("SELECT * FROM income_sources WHERE user_id = :user_id ORDER BY is_active DESC, name"), {"user_id": user.id}).all()
    return [income_response(row) for row in rows]


def create_income(db: DbSession, user: User, payload) -> dict:
    if payload.frequency and payload.frequency not in FREQUENCIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid frequency")
    db.execute(
        text("""
            INSERT INTO income_sources (user_id, name, amount_cents, frequency, interval_count, next_payment_date, destination_account_id, payer, category, is_active, start_date, end_date, notes, source, created_at, updated_at)
            VALUES (:user_id, :name, :amount, :frequency, :interval_count, :next_payment_date, :account_id, :payer, :category, :active, :start_date, :end_date, :notes, 'manual', :now, :now)
        """),
        {"user_id": user.id, "name": payload.name, "amount": _c(payload.amount), "frequency": payload.frequency, "interval_count": payload.interval_count, "next_payment_date": payload.next_payment_date, "account_id": payload.destination_account_id, "payer": payload.payer, "category": payload.category, "active": payload.is_active, "start_date": payload.start_date, "end_date": payload.end_date, "notes": payload.notes, "now": utcnow()},
    )
    row = db.execute(text("SELECT * FROM income_sources WHERE id = last_insert_rowid()")).first()
    db.commit()
    return income_response(row)


def list_recurring(db: DbSession, user: User, filter_value: str = "all") -> list[dict]:
    ensure_seed_data(db, user)
    rows = db.execute(text("SELECT * FROM recurring_expenses WHERE user_id = :user_id ORDER BY is_active DESC, category, name"), {"user_id": user.id}).all()
    items = [recurring_response(row) for row in rows]
    if filter_value == "active":
        return [item for item in items if item["is_active"]]
    if filter_value == "inactive":
        return [item for item in items if not item["is_active"]]
    if filter_value == "complete":
        return [item for item in items if item["completeness"] in {"complete", "inactive"}]
    if filter_value == "incomplete":
        return [item for item in items if "incomplete" in item["completeness"]]
    return items


def create_recurring(db: DbSession, user: User, payload) -> dict:
    if payload.frequency and payload.frequency not in FREQUENCIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid frequency")
    db.execute(
        text("""
            INSERT INTO recurring_expenses (user_id, name, amount_cents, frequency, interval_count, next_due_date, direct_debit, account_id, source_account_text, category, expense_type, owner_group, is_active, variable_amount, aliases, notes, last_paid_date, source, created_at, updated_at)
            VALUES (:user_id, :name, :amount, :frequency, :interval_count, :next_due_date, :direct_debit, :account_id, :source_account_text, :category, :expense_type, :owner_group, :is_active, :variable_amount, :aliases, :notes, :last_paid_date, 'manual', :now, :now)
        """),
        {"user_id": user.id, "name": payload.name, "amount": _c(payload.amount), "frequency": payload.frequency, "interval_count": payload.interval_count, "next_due_date": payload.next_due_date, "direct_debit": payload.direct_debit, "account_id": payload.account_id, "source_account_text": payload.source_account_text, "category": payload.category, "expense_type": payload.expense_type, "owner_group": payload.owner_group, "is_active": payload.is_active, "variable_amount": payload.variable_amount, "aliases": payload.aliases, "notes": payload.notes, "last_paid_date": payload.last_paid_date, "now": utcnow()},
    )
    row = db.execute(text("SELECT * FROM recurring_expenses WHERE id = last_insert_rowid()")).first()
    db.commit()
    return recurring_response(row)


def list_bills(db: DbSession, user: User, filter_value: str = "all") -> list[dict]:
    ensure_seed_data(db, user)
    rows = db.execute(text("SELECT * FROM bills WHERE user_id = :user_id ORDER BY due_date IS NULL, due_date, priority"), {"user_id": user.id}).all()
    items = [bill_response(row) for row in rows]
    if filter_value == "overdue":
        return [item for item in items if item["status"] == "overdue"]
    if filter_value == "due_soon":
        return [item for item in items if item["status"] in {"due_today", "due_soon"}]
    return items


def create_bill(db: DbSession, user: User, payload) -> dict:
    priority = (payload.priority or "normal").lower()
    if priority not in BILL_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid priority")
    amount = _c(payload.amount)
    db.execute(
        text("""
            INSERT INTO bills (user_id, recurring_expense_id, name, provider, bill_type, priority, original_amount_cents, remaining_amount_cents, due_date, account_id, paid_through_date, notes, is_active, source, created_at, updated_at)
            VALUES (:user_id, :recurring_id, :name, :provider, :bill_type, :priority, :amount, :amount, :due_date, :account_id, :paid_through_date, :notes, 1, 'manual', :now, :now)
        """),
        {"user_id": user.id, "recurring_id": payload.recurring_expense_id, "name": payload.name, "provider": payload.provider, "bill_type": payload.bill_type, "priority": priority, "amount": amount, "due_date": payload.due_date, "account_id": payload.account_id, "paid_through_date": payload.paid_through_date, "notes": payload.notes, "now": utcnow()},
    )
    row = db.execute(text("SELECT * FROM bills WHERE id = last_insert_rowid()")).first()
    db.commit()
    return bill_response(row)


def schedule_events(db: DbSession, user: User, start: date, end: date) -> list[dict]:
    ensure_seed_data(db, user)
    events = []
    for row in db.execute(text("SELECT * FROM income_sources WHERE user_id = :user_id AND is_active = 1"), {"user_id": user.id}).all():
        events.extend(occurrences(row.next_payment_date, end, row.amount_cents, row.frequency, row.name, "income", {"category": row.category or "Revenue / Income", "provider": row.payer, "range_start": start}, row.interval_count))
    for row in db.execute(text("SELECT * FROM recurring_expenses WHERE user_id = :user_id AND is_active = 1"), {"user_id": user.id}).all():
        events.extend(occurrences(row.next_due_date, end, row.amount_cents, row.frequency, row.name, "recurring_expense", {"category": row.category or "Miscellaneous", "provider": row.expense_type, "account": row.source_account_text, "range_start": start}, row.interval_count))
    for row in db.execute(text("SELECT * FROM bills WHERE user_id = :user_id AND is_active = 1"), {"user_id": user.id}).all():
        due_date = _as_date(row.due_date)
        if due_date and row.remaining_amount_cents is not None and due_date <= end:
            events.append({"date": due_date.isoformat(), "name": row.name, "amount_cents": row.remaining_amount_cents, "amount": cents_to_decimal(row.remaining_amount_cents), "kind": "bill", "category": row.bill_type or "Financial Obligations", "provider": row.provider, "status": bill_status(due_date, row.paid_at, row.resolved_at, row.remaining_amount_cents, row.original_status)})
    return sorted(events, key=lambda item: (item["date"], item["kind"], item["name"]))


def schedule_summary(db: DbSession, user: User, start: date, end: date) -> dict:
    events = schedule_events(db, user, start, end)
    income = sum(item["amount_cents"] for item in events if item["kind"] == "income")
    commitments = sum(item["amount_cents"] for item in events if item["kind"] != "income")
    return {"start": start.isoformat(), "end": end.isoformat(), "income": cents_to_decimal(income), "commitments": cents_to_decimal(commitments), "net": cents_to_decimal(income - commitments), "events": [{k: v for k, v in item.items() if k != "amount_cents"} for item in events]}


def annual_matrix(db: DbSession, user: User, year: int) -> dict:
    events = schedule_events(db, user, date(year, 1, 1), date(year, 12, 31))
    rows: dict[str, dict] = {}
    for item in events:
        month = int(item["date"][5:7])
        key = f"{item.get('category') or 'Miscellaneous'}::{item['name']}"
        row = rows.setdefault(key, {"category": item.get("category") or "Miscellaneous", "item": item["name"], "months": {m: {"total_cents": 0, "items": []} for m in range(1, 13)}, "total_cents": 0})
        signed = item["amount_cents"] if item["kind"] == "income" else -item["amount_cents"]
        row["months"][month]["total_cents"] += signed
        row["months"][month]["items"].append({k: v for k, v in item.items() if k != "amount_cents"})
        row["total_cents"] += signed
    return {"year": year, "rows": [{"category": row["category"], "item": row["item"], "months": {str(m): {"total": cents_to_decimal(data["total_cents"]), "items": data["items"]} for m, data in row["months"].items()}, "total": cents_to_decimal(row["total_cents"])} for row in rows.values()]}
