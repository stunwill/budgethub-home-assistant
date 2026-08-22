from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow
from . import v1

router = APIRouter(prefix="/api")
DB = Depends(get_db)
USER = Depends(get_current_user)

AUTOMATIC_METHODS = {"direct_debit", "automatic_card_payment"}
MANUAL_METHODS = {"bpay", "bank_transfer", "manual_payment", "cash", "other", "not_set"}
PAYMENT_HANDLING = {"automatic", "manual"}
SCHEDULED_STATUSES = {
    "upcoming",
    "due",
    "overdue",
    "expected_automatically",
    "auto_payment_unconfirmed",
    "paid",
    "skipped",
    "cancelled",
}
DEFAULT_GRACE_DAYS = 3


def default_payment_handling(method: str | None) -> str:
    return "automatic" if method in AUTOMATIC_METHODS else "manual"


def ensure_payment_schema(engine) -> None:
    with engine.begin() as connection:
        def columns(table: str) -> set[str]:
            return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})")).all()}

        def add_column(table: str, definition: str) -> None:
            column = definition.split()[0]
            if column not in columns(table):
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))

        add_column("recurring_expenses", "payment_handling VARCHAR(20)")
        add_column("recurring_expenses", "auto_payment_grace_days INTEGER NOT NULL DEFAULT 3")
        connection.execute(text("""
            UPDATE recurring_expenses
            SET payment_handling = CASE
                WHEN payment_method IN ('direct_debit','automatic_card_payment') THEN 'automatic'
                ELSE 'manual'
            END
            WHERE payment_handling IS NULL OR payment_handling = ''
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS scheduled_payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                recurring_expense_id INTEGER NOT NULL,
                expected_date DATE NOT NULL,
                expected_amount_cents INTEGER,
                status VARCHAR(40) NOT NULL,
                payment_method VARCHAR(40) NOT NULL,
                payment_handling VARCHAR(20) NOT NULL,
                account_id INTEGER,
                card_id INTEGER,
                actual_date DATE,
                actual_amount_cents INTEGER,
                matched_transaction_id INTEGER,
                match_confidence VARCHAR(20),
                confirmation_source VARCHAR(40),
                note TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(user_id, recurring_expense_id, expected_date),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(recurring_expense_id) REFERENCES recurring_expenses(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id),
                FOREIGN KEY(card_id) REFERENCES cards(id),
                FOREIGN KEY(matched_transaction_id) REFERENCES transactions(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS scheduled_payment_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                scheduled_payment_id INTEGER NOT NULL,
                from_status VARCHAR(40),
                to_status VARCHAR(40) NOT NULL,
                source VARCHAR(40) NOT NULL,
                note TEXT,
                created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(scheduled_payment_id) REFERENCES scheduled_payments(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS recurring_match_mappings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                recurring_expense_id INTEGER NOT NULL,
                merchant_key VARCHAR(180) NOT NULL,
                account_id INTEGER,
                confirmed_count INTEGER NOT NULL DEFAULT 1,
                last_confirmed_at DATETIME NOT NULL,
                UNIQUE(user_id, recurring_expense_id, merchant_key, account_id)
            )
        """))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scheduled_payment_attention ON scheduled_payments(user_id,status,expected_date)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_payment_tx_unique ON scheduled_payments(user_id,matched_transaction_id) WHERE matched_transaction_id IS NOT NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scheduled_payment_history ON scheduled_payment_history(user_id,scheduled_payment_id,created_at)"))

        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (17)"))
        elif int(current) < 17:
            connection.execute(text("UPDATE schema_version SET version=17"))


def _status_for(expected_date: date, handling: str, grace_days: int, today: date) -> str:
    if expected_date > today:
        return "upcoming"
    if handling == "automatic":
        if expected_date + timedelta(days=grace_days) < today:
            return "auto_payment_unconfirmed"
        return "expected_automatically"
    if expected_date == today:
        return "due"
    return "overdue"


def _scheduled_response(row: Any) -> dict[str, Any]:
    data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
    expected = data.get("expected_amount_cents")
    actual = data.get("actual_amount_cents")
    return {
        "id": data["id"],
        "recurring_expense_id": data["recurring_expense_id"],
        "name": data.get("name"),
        "expected_date": data["expected_date"],
        "expected_amount": cents_to_decimal(expected) if expected is not None else None,
        "status": data["status"],
        "payment_method": data["payment_method"],
        "payment_method_label": v1.PAYMENT_METHODS.get(data["payment_method"], data["payment_method"].replace("_", " ").title()),
        "payment_handling": data["payment_handling"],
        "account_id": data.get("account_id"),
        "account_name": data.get("account_name"),
        "card_id": data.get("card_id"),
        "card_name": data.get("card_name"),
        "linked_account_name": data.get("linked_account_name"),
        "actual_date": data.get("actual_date"),
        "actual_amount": cents_to_decimal(actual) if actual is not None else None,
        "matched_transaction_id": data.get("matched_transaction_id"),
        "match_confidence": data.get("match_confidence"),
        "confirmation_source": data.get("confirmation_source"),
        "note": data.get("note"),
    }


def ensure_scheduled_payments(db: DbSession, user: User, horizon_days: int = 120, today: date | None = None) -> None:
    today = today or date.today()
    end = today + timedelta(days=horizon_days)
    rows = db.execute(text("""
        SELECT r.*, c.account_id AS card_account_id
        FROM recurring_expenses r
        LEFT JOIN cards c ON c.id=r.card_id AND c.user_id=r.user_id
        WHERE r.user_id=:uid AND r.is_active=1 AND r.next_due_date IS NOT NULL
    """), {"uid": user.id}).mappings().all()
    now = utcnow()
    for row in rows:
        due = row["next_due_date"] if isinstance(row["next_due_date"], date) else date.fromisoformat(str(row["next_due_date"])[:10])
        if due > end:
            continue
        method = row["payment_method"] or ("direct_debit" if row["direct_debit"] else "not_set")
        handling = row.get("payment_handling") or default_payment_handling(method)
        grace = int(row.get("auto_payment_grace_days") or DEFAULT_GRACE_DAYS)
        account_id = int(row["card_account_id"]) if method == "automatic_card_payment" and row.get("card_account_id") else row["account_id"]
        status_name = _status_for(due, handling, grace, today)
        existing = db.execute(text("SELECT id,status FROM scheduled_payments WHERE user_id=:uid AND recurring_expense_id=:rid AND expected_date=:due"), {"uid": user.id, "rid": row["id"], "due": due}).mappings().first()
        if existing:
            if existing["status"] not in {"paid", "skipped", "cancelled"} and existing["status"] != status_name:
                db.execute(text("UPDATE scheduled_payments SET status=:status,updated_at=:now WHERE id=:id"), {"status": status_name, "now": now, "id": existing["id"]})
                db.execute(text("INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,created_at) VALUES(:uid,:sid,:from_status,:to_status,'system',:now)"), {"uid": user.id, "sid": existing["id"], "from_status": existing["status"], "to_status": status_name, "now": now})
            continue
        db.execute(text("""
            INSERT INTO scheduled_payments(user_id,recurring_expense_id,expected_date,expected_amount_cents,status,payment_method,payment_handling,account_id,card_id,created_at,updated_at)
            VALUES(:uid,:rid,:due,:amount,:status,:method,:handling,:account_id,:card_id,:now,:now)
        """), {"uid": user.id, "rid": row["id"], "due": due, "amount": row["amount_cents"], "status": status_name, "method": method, "handling": handling, "account_id": account_id, "card_id": row["card_id"], "now": now})
        sid = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
        db.execute(text("INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,created_at) VALUES(:uid,:sid,NULL,:status,'system',:now)"), {"uid": user.id, "sid": sid, "status": status_name, "now": now})
    db.commit()


@router.get("/payment-methods")
def payment_methods(current_user: User = USER):
    return [{"id": key, "label": label, "default_handling": default_payment_handling(key)} for key, label in v1.PAYMENT_METHODS.items()]


@router.get("/scheduled-payments")
def scheduled_payments(status_filter: str | None = None, current_user: User = USER, db: DbSession = DB):
    ensure_scheduled_payments(db, current_user)
    sql = """
        SELECT sp.*,r.name,a.name AS account_name,
               CASE WHEN c.id IS NULL THEN NULL ELSE c.name || ' ••••' || c.last_four END AS card_name,
               ca.name AS linked_account_name
        FROM scheduled_payments sp
        JOIN recurring_expenses r ON r.id=sp.recurring_expense_id
        LEFT JOIN accounts a ON a.id=sp.account_id
        LEFT JOIN cards c ON c.id=sp.card_id
        LEFT JOIN accounts ca ON ca.id=c.account_id
        WHERE sp.user_id=:uid
    """
    params: dict[str, Any] = {"uid": current_user.id}
    if status_filter:
        sql += " AND sp.status=:status"
        params["status"] = status_filter
    sql += " ORDER BY sp.expected_date,sp.id"
    return [_scheduled_response(row) for row in db.execute(text(sql), params).all()]


@router.get("/payments/attention")
def payment_attention(current_user: User = USER, db: DbSession = DB):
    ensure_scheduled_payments(db, current_user)
    rows = db.execute(text("""
        SELECT sp.*,r.name,a.name AS account_name,
               CASE WHEN c.id IS NULL THEN NULL ELSE c.name || ' ••••' || c.last_four END AS card_name,
               ca.name AS linked_account_name
        FROM scheduled_payments sp
        JOIN recurring_expenses r ON r.id=sp.recurring_expense_id
        LEFT JOIN accounts a ON a.id=sp.account_id
        LEFT JOIN cards c ON c.id=sp.card_id
        LEFT JOIN accounts ca ON ca.id=c.account_id
        WHERE sp.user_id=:uid AND sp.status IN ('overdue','due','auto_payment_unconfirmed')
        ORDER BY CASE sp.status WHEN 'overdue' THEN 0 WHEN 'due' THEN 1 ELSE 2 END,sp.expected_date
    """), {"uid": current_user.id}).all()
    return [_scheduled_response(row) for row in rows]


class ManualPaymentRequest(BaseModel):
    paid_date: date = Field(default_factory=date.today)
    paid_amount: str | None = None
    note: str | None = None


@router.post("/scheduled-payments/{payment_id}/mark-paid")
def mark_paid(payment_id: int, payload: ManualPaymentRequest, current_user: User = USER, db: DbSession = DB):
    row = db.execute(text("SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    if row["status"] in {"skipped", "cancelled"}:
        raise HTTPException(status_code=409, detail="Skipped or cancelled payments cannot be marked paid")
    actual = parse_money(payload.paid_amount) if payload.paid_amount not in (None, "") else row["expected_amount_cents"]
    now = utcnow()
    db.execute(text("UPDATE scheduled_payments SET status='paid',actual_date=:actual_date,actual_amount_cents=:actual,note=:note,confirmation_source='manual',updated_at=:now WHERE id=:id"), {"actual_date": payload.paid_date, "actual": actual, "note": payload.note, "now": now, "id": payment_id})
    db.execute(text("INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,note,created_at) VALUES(:uid,:sid,:from_status,'paid','manual',:note,:now)"), {"uid": current_user.id, "sid": payment_id, "from_status": row["status"], "note": payload.note, "now": now})
    db.commit()
    return {"status": "paid", "scheduled_payment_id": payment_id, "actual_date": payload.paid_date, "actual_amount": cents_to_decimal(actual)}


@router.post("/scheduled-payments/{payment_id}/skip")
def skip_payment(payment_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    row = db.execute(text("SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    if row["status"] == "paid":
        raise HTTPException(status_code=409, detail="Paid payments cannot be skipped")
    note = payload.get("note")
    now = utcnow()
    db.execute(text("UPDATE scheduled_payments SET status='skipped',note=:note,updated_at=:now WHERE id=:id"), {"note": note, "now": now, "id": payment_id})
    db.execute(text("INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,note,created_at) VALUES(:uid,:sid,:from_status,'skipped','manual',:note,:now)"), {"uid": current_user.id, "sid": payment_id, "from_status": row["status"], "note": note, "now": now})
    db.commit()
    return {"status": "skipped", "scheduled_payment_id": payment_id}


class MatchRequest(BaseModel):
    transaction_id: int
    confidence: str = "high"


@router.post("/scheduled-payments/{payment_id}/match")
def match_payment(payment_id: int, payload: MatchRequest, current_user: User = USER, db: DbSession = DB):
    payment = db.execute(text("SELECT * FROM scheduled_payments WHERE id=:id AND user_id=:uid"), {"id": payment_id, "uid": current_user.id}).mappings().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Scheduled Payment not found")
    if payment["matched_transaction_id"]:
        raise HTTPException(status_code=409, detail="Scheduled Payment is already matched")
    transaction = db.execute(text("SELECT * FROM transactions WHERE id=:id AND user_id=:uid"), {"id": payload.transaction_id, "uid": current_user.id}).mappings().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    existing = db.execute(text("SELECT id FROM scheduled_payments WHERE user_id=:uid AND matched_transaction_id=:tx"), {"uid": current_user.id, "tx": payload.transaction_id}).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="Transaction is already matched to another Scheduled Payment")
    confidence = payload.confidence.lower()
    if confidence not in {"high", "medium", "low"}:
        raise HTTPException(status_code=400, detail="Unsupported match confidence")
    actual_date = transaction.get("transaction_date") or transaction.get("date")
    actual_amount = abs(int(transaction["amount_cents"]))
    now = utcnow()
    db.execute(text("UPDATE scheduled_payments SET status='paid',actual_date=:actual_date,actual_amount_cents=:actual,matched_transaction_id=:tx,match_confidence=:confidence,confirmation_source='transaction_match',updated_at=:now WHERE id=:id"), {"actual_date": actual_date, "actual": actual_amount, "tx": payload.transaction_id, "confidence": confidence, "now": now, "id": payment_id})
    db.execute(text("INSERT INTO scheduled_payment_history(user_id,scheduled_payment_id,from_status,to_status,source,created_at) VALUES(:uid,:sid,:from_status,'paid','transaction_match',:now)"), {"uid": current_user.id, "sid": payment_id, "from_status": payment["status"], "now": now})
    merchant = str(transaction.get("merchant") or transaction.get("description") or "").strip().casefold()
    if merchant:
        db.execute(text("""
            INSERT INTO recurring_match_mappings(user_id,recurring_expense_id,merchant_key,account_id,confirmed_count,last_confirmed_at)
            VALUES(:uid,:rid,:merchant,:account_id,1,:now)
            ON CONFLICT(user_id,recurring_expense_id,merchant_key,account_id)
            DO UPDATE SET confirmed_count=confirmed_count+1,last_confirmed_at=:now
        """), {"uid": current_user.id, "rid": payment["recurring_expense_id"], "merchant": merchant, "account_id": transaction.get("account_id"), "now": now})
    db.commit()
    return {"status": "paid", "scheduled_payment_id": payment_id, "transaction_id": payload.transaction_id, "actual_amount": cents_to_decimal(actual_amount), "match_confidence": confidence}


@router.get("/payments/match-candidates")
def match_candidates(current_user: User = USER, db: DbSession = DB):
    ensure_scheduled_payments(db, current_user)
    payments = db.execute(text("""
        SELECT sp.*,r.name,r.payee_merchant FROM scheduled_payments sp
        JOIN recurring_expenses r ON r.id=sp.recurring_expense_id
        WHERE sp.user_id=:uid AND sp.status NOT IN ('paid','skipped','cancelled')
    """), {"uid": current_user.id}).mappings().all()
    transactions = db.execute(text("SELECT * FROM transactions WHERE user_id=:uid ORDER BY transaction_date DESC,id DESC LIMIT 250"), {"uid": current_user.id}).mappings().all()
    output = []
    for tx in transactions:
        if db.execute(text("SELECT id FROM scheduled_payments WHERE user_id=:uid AND matched_transaction_id=:tx"), {"uid": current_user.id, "tx": tx["id"]}).scalar():
            continue
        tx_date = tx.get("transaction_date") or tx.get("date")
        if not tx_date:
            continue
        tx_date = tx_date if isinstance(tx_date, date) else date.fromisoformat(str(tx_date)[:10])
        tx_amount = abs(int(tx["amount_cents"]))
        tx_text = str(tx.get("merchant") or tx.get("description") or "").casefold()
        for payment in payments:
            expected_date = payment["expected_date"] if isinstance(payment["expected_date"], date) else date.fromisoformat(str(payment["expected_date"])[:10])
            days = abs((tx_date - expected_date).days)
            if days > 7:
                continue
            expected = payment["expected_amount_cents"]
            amount_delta = abs(tx_amount - expected) if expected is not None else 0
            amount_ratio = amount_delta / max(expected or tx_amount or 1, 1)
            text_match = bool(payment.get("payee_merchant") and str(payment["payee_merchant"]).casefold() in tx_text)
            account_match = payment.get("account_id") is None or int(payment["account_id"]) == int(tx.get("account_id") or -1)
            if amount_ratio <= 0.02 and days <= 2 and account_match:
                confidence = "high"
            elif amount_ratio <= 0.10 and days <= 4:
                confidence = "medium"
            elif text_match and days <= 7:
                confidence = "medium"
            else:
                continue
            output.append({
                "transaction_id": tx["id"],
                "transaction_date": tx_date,
                "transaction_amount": cents_to_decimal(tx_amount),
                "transaction_description": tx.get("merchant") or tx.get("description"),
                "scheduled_payment_id": payment["id"],
                "recurring_expense_id": payment["recurring_expense_id"],
                "expense_name": payment["name"],
                "expected_date": expected_date,
                "expected_amount": cents_to_decimal(expected) if expected is not None else None,
                "difference": cents_to_decimal(amount_delta),
                "confidence": confidence,
            })
    return output
