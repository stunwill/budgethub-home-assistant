from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .ledger import get_account, signed_amount_cents
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter(prefix="/api/bank-connections")
DB = Depends(get_db)
USER = Depends(get_current_user)

BANK_SCHEMA_VERSION = 11
CONNECTED_ACCOUNT_TYPES = {"transaction", "savings", "credit_card", "mortgage", "personal_loan", "vehicle_loan"}
OUTGOING_WORDS = ("woolworths", "netflix", "spotify", "telstra", "powershop", "jb hi-fi", "fuel", "shell", "coles")
TRANSFER_WORDS = ("transfer", "savings", "credit card payment", "payment received", "internal")


class MockBankProvider:
    provider = "mock_cdr"
    name = "Mock Australian Bank Provider"

    def institutions(self) -> list[dict[str, str]]:
        return [
            {"id": "mock-bank-au", "name": "Mock Bank Australia", "provider": self.provider},
            {"id": "mock-credit-au", "name": "Mock Credit Union", "provider": self.provider},
        ]

    def accounts(self, institution_id: str) -> list[dict[str, Any]]:
        institution = "Mock Credit Union" if institution_id == "mock-credit-au" else "Mock Bank Australia"
        return [
            {"provider_account_id": f"{institution_id}:everyday", "name": "Everyday Account", "account_type": "transaction", "institution": institution, "masked_identifier": "•••• 1234", "current_balance": "8420.75", "available_balance": "8220.75"},
            {"provider_account_id": f"{institution_id}:saver", "name": "Savings Account", "account_type": "savings", "institution": institution, "masked_identifier": "•••• 8812", "current_balance": "6500.00", "available_balance": "6500.00"},
            {"provider_account_id": f"{institution_id}:visa", "name": "Visa Card", "account_type": "credit_card", "institution": institution, "masked_identifier": "•••• 4444", "current_balance": "-1250.30", "available_balance": "2749.70"},
        ]

    def transactions(self, provider_account_id: str, sync_number: int) -> tuple[list[dict[str, Any]], str]:
        today = date(2026, 8, 17)
        if provider_account_id.endswith(":saver"):
            rows = [
                {"id": "saver-transfer-in-001", "date": today.isoformat(), "posted_date": today.isoformat(), "amount": "500.00", "description": "Internal transfer from Everyday", "merchant": "Internal Transfer", "status": "posted", "pending_key": "transfer-500-20260817"},
            ]
        elif provider_account_id.endswith(":visa"):
            rows = [
                {"id": "visa-woolworths-001", "date": (today - timedelta(days=2)).isoformat(), "posted_date": (today - timedelta(days=1)).isoformat(), "amount": "82.14", "description": "WOOLWORTHS 1234 MILDURA", "merchant": "Woolworths", "status": "posted"},
                {"id": "visa-payment-001", "date": today.isoformat(), "posted_date": today.isoformat(), "amount": "500.00", "description": "Credit card payment received", "merchant": "Internal Transfer", "status": "posted", "pending_key": "transfer-500-20260817"},
            ]
        else:
            rows = [
                {"id": "everyday-salary-001", "date": (today + timedelta(days=1)).isoformat(), "posted_date": (today + timedelta(days=1)).isoformat(), "amount": "2100.00", "description": "PAYROLL SALARY", "merchant": "Payroll", "status": "posted"},
                {"id": "everyday-netflix-001", "date": (today + timedelta(days=2)).isoformat(), "posted_date": (today + timedelta(days=2)).isoformat(), "amount": "29.00", "description": "NETFLIX.COM", "merchant": "Netflix", "status": "posted"},
                {"id": "everyday-transfer-out-001", "date": today.isoformat(), "posted_date": today.isoformat(), "amount": "500.00", "description": "Internal transfer to Savings", "merchant": "Internal Transfer", "status": "posted", "pending_key": "transfer-500-20260817"},
                {"id": "everyday-fuel-pending", "date": today.isoformat(), "posted_date": None, "amount": "50.00", "description": "PENDING SHELL MILDURA", "merchant": "Shell", "status": "pending", "pending_key": "fuel-shell-50"},
            ]
            if sync_number >= 2:
                rows[-1] = {"id": "everyday-fuel-posted", "date": today.isoformat(), "posted_date": today.isoformat(), "amount": "50.00", "description": "SHELL MILDURA", "merchant": "Shell", "status": "posted", "pending_key": "fuel-shell-50"}
                rows.append({"id": f"everyday-coles-{sync_number}", "date": (today + timedelta(days=sync_number)).isoformat(), "posted_date": (today + timedelta(days=sync_number)).isoformat(), "amount": "64.30", "description": "COLES MILDURA", "merchant": "Coles", "status": "posted"})
        return rows, f"mock-cursor-{sync_number}"


MOCK_PROVIDER = MockBankProvider()


def provider_for(provider: str) -> MockBankProvider:
    if provider != MOCK_PROVIDER.provider:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only the mock CDR provider is available in v0.12.0")
    return MOCK_PROVIDER


def _table_exists(db: DbSession, table: str) -> bool:
    return bool(db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table}).scalar())


def _columns(db: DbSession, table: str) -> set[str]:
    return {row[1] for row in db.execute(text(f"PRAGMA table_info({table})")).all()} if _table_exists(db, table) else set()


def _add_column(db: DbSession, table: str, column: str, definition: str) -> None:
    if column not in _columns(db, table):
        db.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def ensure_banking_schema(db: DbSession) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS bank_connections (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, provider VARCHAR(80) NOT NULL,
            provider_connection_id VARCHAR(180) NOT NULL, institution_id VARCHAR(180) NOT NULL,
            institution_name VARCHAR(180) NOT NULL, status VARCHAR(40) NOT NULL DEFAULT 'connected',
            consent_status VARCHAR(40) NOT NULL DEFAULT 'mock', connected_at DATETIME NOT NULL,
            last_successful_sync DATETIME, last_attempted_sync DATETIME, consent_expiry DATE,
            error_state TEXT, sync_cursor TEXT, is_mock BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id), UNIQUE(user_id, provider, provider_connection_id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS external_accounts (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, bank_connection_id INTEGER NOT NULL,
            provider VARCHAR(80) NOT NULL, provider_account_id VARCHAR(180) NOT NULL,
            fynvo_account_id INTEGER, institution_name VARCHAR(180), account_name VARCHAR(180) NOT NULL,
            account_type VARCHAR(40), masked_identifier VARCHAR(40), current_balance_cents INTEGER,
            available_balance_cents INTEGER, balance_timestamp DATETIME, status VARCHAR(40) NOT NULL DEFAULT 'discovered',
            ignored BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(bank_connection_id) REFERENCES bank_connections(id),
            FOREIGN KEY(fynvo_account_id) REFERENCES accounts(id), UNIQUE(user_id, provider, provider_account_id)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS bank_transaction_identities (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, external_account_id INTEGER NOT NULL,
            transaction_id INTEGER NOT NULL, provider VARCHAR(80) NOT NULL,
            provider_transaction_id VARCHAR(180), pending_key VARCHAR(180), fingerprint VARCHAR(180) NOT NULL,
            status VARCHAR(40) NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(external_account_id) REFERENCES external_accounts(id),
            FOREIGN KEY(transaction_id) REFERENCES transactions(id), UNIQUE(user_id, provider, fingerprint)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS bank_sync_history (
            id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, bank_connection_id INTEGER NOT NULL,
            started_at DATETIME NOT NULL, completed_at DATETIME, status VARCHAR(40) NOT NULL,
            added_count INTEGER NOT NULL DEFAULT 0, updated_count INTEGER NOT NULL DEFAULT 0,
            duplicate_count INTEGER NOT NULL DEFAULT 0, review_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT, created_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(bank_connection_id) REFERENCES bank_connections(id)
        )
    """))
    _add_column(db, "transactions", "posted_date", "DATE")
    _add_column(db, "transactions", "provider", "VARCHAR(80)")
    _add_column(db, "transactions", "provider_account_id", "VARCHAR(180)")
    _add_column(db, "transactions", "provider_transaction_id", "VARCHAR(180)")
    _add_column(db, "transactions", "pending_key", "VARCHAR(180)")
    _add_column(db, "transactions", "source_fingerprint", "VARCHAR(180)")
    _add_column(db, "accounts", "connection_status", "VARCHAR(40)")
    _add_column(db, "accounts", "available_balance_cents", "INTEGER")
    _add_column(db, "accounts", "balance_timestamp", "DATETIME")
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_bank_connections_user ON bank_connections(user_id, status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_external_accounts_connection ON external_accounts(user_id, bank_connection_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_bank_tx_identity_account ON bank_transaction_identities(user_id, external_account_id, status)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_provider_identity ON transactions(user_id, provider, provider_transaction_id, pending_key)"))
    current = db.execute(text("SELECT max(version) FROM schema_version")).scalar()
    if current is None:
        db.execute(text("INSERT INTO schema_version (version) VALUES (:version)"), {"version": BANK_SCHEMA_VERSION})
    elif int(current) < BANK_SCHEMA_VERSION:
        db.execute(text("UPDATE schema_version SET version = :version"), {"version": BANK_SCHEMA_VERSION})
    db.commit()


def _money(value: Any) -> int:
    return parse_money(str(value or "0.00"))


def _normalise_merchant(description: str, merchant: str | None) -> str | None:
    text_value = (merchant or description or "").lower()
    known = {"woolworths": "Woolworths", "coles": "Coles", "netflix": "Netflix", "spotify": "Spotify", "payroll": "Payroll", "shell": "Shell", "jb hi-fi": "JB Hi-Fi"}
    for key, label in known.items():
        if key in text_value:
            return label
    words = [word for word in (merchant or description or "").replace(".", " ").split() if word]
    return words[0].title() if words else None


def _direction(account_type: str, description: str, amount_cents: int) -> str:
    text_value = description.lower()
    if any(word in text_value for word in TRANSFER_WORDS):
        return "transfer"
    if account_type == "credit_card":
        return "expense" if not any(word in text_value for word in ("payment", "refund", "credit")) else "transfer"
    if "salary" in text_value or "payroll" in text_value:
        return "income"
    if any(word in text_value for word in OUTGOING_WORDS):
        return "expense"
    return "income" if amount_cents > 0 else "expense"


def _fingerprint(provider: str, provider_account_id: str, row: dict[str, Any]) -> str:
    key = "|".join([provider, provider_account_id, str(row.get("id") or ""), str(row.get("pending_key") or ""), str(row.get("date") or ""), str(row.get("amount") or ""), str(row.get("description") or "").lower()])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:48]


def _connection_row(db: DbSession, user: User, connection_id: int) -> dict[str, Any]:
    row = db.execute(text("SELECT * FROM bank_connections WHERE id=:id AND user_id=:user_id"), {"id": connection_id, "user_id": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bank connection not found")
    return dict(row)


def _connection_response(db: DbSession, row: dict[str, Any]) -> dict[str, Any]:
    accounts = db.execute(text("SELECT * FROM external_accounts WHERE bank_connection_id=:id ORDER BY account_name"), {"id": row["id"]}).mappings().all()
    return {
        "id": row["id"],
        "provider": row["provider"],
        "provider_label": MOCK_PROVIDER.name if row["provider"] == MOCK_PROVIDER.provider else row["provider"],
        "institution_id": row["institution_id"],
        "institution_name": row["institution_name"],
        "status": row["status"],
        "consent_status": row["consent_status"],
        "connected_at": str(row["connected_at"]),
        "last_successful_sync": str(row["last_successful_sync"]) if row["last_successful_sync"] else None,
        "last_attempted_sync": str(row["last_attempted_sync"]) if row["last_attempted_sync"] else None,
        "consent_expiry": str(row["consent_expiry"]) if row["consent_expiry"] else None,
        "error_state": row["error_state"],
        "is_mock": bool(row["is_mock"]),
        "accounts": [_external_account_response(item) for item in accounts],
    }


def _external_account_response(row: Any) -> dict[str, Any]:
    data = dict(row)
    return {
        "id": data["id"],
        "bank_connection_id": data["bank_connection_id"],
        "provider_account_id": data["provider_account_id"],
        "fynvo_account_id": data["fynvo_account_id"],
        "institution_name": data["institution_name"],
        "name": data["account_name"],
        "account_type": data["account_type"],
        "masked_identifier": data["masked_identifier"],
        "current_balance": cents_to_decimal(data["current_balance_cents"] or 0),
        "available_balance": cents_to_decimal(data["available_balance_cents"] or 0),
        "balance_timestamp": str(data["balance_timestamp"]) if data["balance_timestamp"] else None,
        "status": data["status"],
        "ignored": bool(data["ignored"]),
    }


def _upsert_external_account(db: DbSession, user: User, connection_id: int, provider: str, account: dict[str, Any]) -> None:
    now = utcnow()
    existing = db.execute(text("SELECT id, fynvo_account_id FROM external_accounts WHERE user_id=:user_id AND provider=:provider AND provider_account_id=:provider_account_id"), {"user_id": user.id, "provider": provider, "provider_account_id": account["provider_account_id"]}).mappings().first()
    params = {"user_id": user.id, "connection_id": connection_id, "provider": provider, "provider_account_id": account["provider_account_id"], "institution": account["institution"], "name": account["name"], "account_type": account["account_type"], "masked": account["masked_identifier"], "current": _money(account["current_balance"]), "available": _money(account["available_balance"]), "now": now}
    if existing:
        db.execute(text("""UPDATE external_accounts SET institution_name=:institution, account_name=:name, account_type=:account_type, masked_identifier=:masked, current_balance_cents=:current, available_balance_cents=:available, balance_timestamp=:now, updated_at=:now WHERE id=:id"""), {**params, "id": existing["id"]})
    else:
        db.execute(text("""INSERT INTO external_accounts (user_id, bank_connection_id, provider, provider_account_id, institution_name, account_name, account_type, masked_identifier, current_balance_cents, available_balance_cents, balance_timestamp, status, created_at, updated_at)
            VALUES (:user_id, :connection_id, :provider, :provider_account_id, :institution, :name, :account_type, :masked, :current, :available, :now, 'discovered', :now, :now)"""), params)


def _create_linked_account(db: DbSession, user: User, external_account: dict[str, Any]) -> int:
    now = utcnow()
    account_type = external_account.get("account_type") if external_account.get("account_type") in CONNECTED_ACCOUNT_TYPES else "transaction"
    db.execute(text("""INSERT INTO accounts (user_id, name, account_type, institution, opening_balance_cents, description, account_suffix, icon, color, is_active, connection_status, available_balance_cents, balance_timestamp, created_at, updated_at)
        VALUES (:user_id, :name, :account_type, :institution, :balance, :description, :suffix, 'bank', '#0f6fff', 1, 'connected', :available, :now, :now, :now)"""), {"user_id": user.id, "name": external_account["account_name"], "account_type": account_type, "institution": external_account["institution_name"], "balance": int(external_account.get("current_balance_cents") or 0), "available": int(external_account.get("available_balance_cents") or 0), "description": "Created from bank connection. Historical transactions remain source-labelled as Bank Sync.", "suffix": str(external_account.get("masked_identifier") or "")[-4:], "now": now})
    return int(db.execute(text("SELECT last_insert_rowid()")).scalar())


def _update_account_balance_metadata(db: DbSession, fynvo_account_id: int, external_account: dict[str, Any]) -> None:
    db.execute(text("UPDATE accounts SET institution=:institution, account_suffix=:suffix, connection_status='connected', available_balance_cents=:available, balance_timestamp=:now, updated_at=:now WHERE id=:account_id"), {"account_id": fynvo_account_id, "institution": external_account["institution_name"], "suffix": str(external_account.get("masked_identifier") or "")[-4:], "available": int(external_account.get("available_balance_cents") or 0), "now": utcnow()})


def _insert_or_update_transaction(db: DbSession, user: User, external_account: dict[str, Any], row: dict[str, Any]) -> str:
    account_id = external_account.get("fynvo_account_id")
    if not account_id:
        return "ignored"
    account = get_account(db, user, int(account_id))
    provider = external_account["provider"]
    provider_account_id = external_account["provider_account_id"]
    provider_transaction_id = str(row.get("id") or "")
    pending_key = row.get("pending_key")
    fingerprint = _fingerprint(provider, provider_account_id, row)
    existing = db.execute(text("""SELECT t.id, t.status FROM transactions t JOIN bank_transaction_identities bti ON bti.transaction_id=t.id
        WHERE t.user_id=:user_id AND bti.provider=:provider AND (bti.fingerprint=:fingerprint OR (:provider_transaction_id != '' AND bti.provider_transaction_id=:provider_transaction_id) OR (:pending_key IS NOT NULL AND bti.pending_key=:pending_key))"""), {"user_id": user.id, "provider": provider, "fingerprint": fingerprint, "provider_transaction_id": provider_transaction_id, "pending_key": pending_key}).mappings().first()
    amount = _money(row.get("amount"))
    direction = _direction(account.account_type, row.get("description") or "", amount)
    tx_type = "transfer" if direction == "transfer" else direction
    signed = amount if tx_type == "transfer" else signed_amount_cents(account, tx_type, amount)
    tx_status = "pending" if row.get("status") == "pending" else "cleared"
    merchant = _normalise_merchant(row.get("description") or "", row.get("merchant"))
    tx_date = date.fromisoformat(str(row.get("date"))[:10])
    posted_date = date.fromisoformat(str(row.get("posted_date"))[:10]) if row.get("posted_date") else None
    now = utcnow()
    if existing:
        db.execute(text("""UPDATE transactions SET status=:status, posted_date=:posted_date, amount_cents=:amount, description=:description, merchant=:merchant, raw_description=:raw, provider_transaction_id=:provider_transaction_id, pending_key=:pending_key, source_fingerprint=:fingerprint, updated_at=:now WHERE id=:id"""), {"id": existing["id"], "status": tx_status, "posted_date": posted_date, "amount": signed, "description": row.get("description") or merchant or "Bank transaction", "merchant": merchant, "raw": row.get("description"), "provider_transaction_id": provider_transaction_id, "pending_key": pending_key, "fingerprint": fingerprint, "now": now})
        db.execute(text("UPDATE bank_transaction_identities SET provider_transaction_id=:provider_transaction_id, pending_key=:pending_key, fingerprint=:fingerprint, status=:status, updated_at=:now WHERE transaction_id=:id"), {"id": existing["id"], "provider_transaction_id": provider_transaction_id, "pending_key": pending_key, "fingerprint": fingerprint, "status": tx_status, "now": now})
        return "updated" if existing["status"] != tx_status else "duplicate"
    db.execute(text("""INSERT INTO transactions (user_id, account_id, transaction_date, posted_date, amount_cents, transaction_type, description, merchant, category, source, status, raw_description, external_id, provider, provider_account_id, provider_transaction_id, pending_key, source_fingerprint, reconciliation_state, created_at, updated_at)
        VALUES (:user_id, :account_id, :date, :posted_date, :amount, :tx_type, :description, :merchant, :category, 'bank_sync', :status, :raw, :external_id, :provider, :provider_account_id, :provider_transaction_id, :pending_key, :fingerprint, 'unmatched', :now, :now)"""), {"user_id": user.id, "account_id": account.id, "date": tx_date, "posted_date": posted_date, "amount": signed, "tx_type": tx_type, "description": row.get("description") or merchant or "Bank transaction", "merchant": merchant, "category": None, "status": tx_status, "raw": row.get("description"), "external_id": provider_transaction_id, "provider": provider, "provider_account_id": provider_account_id, "provider_transaction_id": provider_transaction_id, "pending_key": pending_key, "fingerprint": fingerprint, "now": now})
    tx_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.execute(text("""INSERT INTO bank_transaction_identities (user_id, external_account_id, transaction_id, provider, provider_transaction_id, pending_key, fingerprint, status, created_at, updated_at)
        VALUES (:user_id, :external_account_id, :transaction_id, :provider, :provider_transaction_id, :pending_key, :fingerprint, :status, :now, :now)"""), {"user_id": user.id, "external_account_id": external_account["id"], "transaction_id": tx_id, "provider": provider, "provider_transaction_id": provider_transaction_id, "pending_key": pending_key, "fingerprint": fingerprint, "status": tx_status, "now": now})
    _suggest_reconciliation(db, user, tx_id, tx_date, amount, tx_type, merchant)
    return "added"


def _suggest_reconciliation(db: DbSession, user: User, tx_id: int, tx_date: date, amount: int, tx_type: str, merchant: str | None) -> None:
    if tx_type == "transfer":
        return
    source_type = None
    source_id = None
    expected = amount
    confidence = 0
    if tx_type == "income":
        row = db.execute(text("SELECT id, amount_cents FROM income_sources WHERE user_id=:user_id AND amount_cents BETWEEN :low AND :high ORDER BY ABS(julianday(next_payment_date)-julianday(:date)) LIMIT 1"), {"user_id": user.id, "low": amount - 5000, "high": amount + 5000, "date": tx_date}).mappings().first()
        if row:
            source_type, source_id, expected, confidence = "income", row["id"], int(row["amount_cents"] or amount), 80
    else:
        row = db.execute(text("SELECT id, remaining_amount_cents FROM bills WHERE user_id=:user_id AND remaining_amount_cents BETWEEN :low AND :high AND (paid_at IS NULL AND resolved_at IS NULL) ORDER BY ABS(julianday(due_date)-julianday(:date)) LIMIT 1"), {"user_id": user.id, "low": amount - 5000, "high": amount + 5000, "date": tx_date}).mappings().first()
        if row:
            source_type, source_id, expected, confidence = "bill", row["id"], int(row["remaining_amount_cents"] or amount), 85
        elif merchant:
            row = db.execute(text("SELECT id, estimated_amount_cents FROM planned_spending WHERE user_id=:user_id AND estimated_amount_cents BETWEEN :low AND :high AND status IN ('planned','committed') ORDER BY ABS(julianday(planned_date)-julianday(:date)) LIMIT 1"), {"user_id": user.id, "low": amount - 10000, "high": amount + 10000, "date": tx_date}).mappings().first()
            if row:
                source_type, source_id, expected, confidence = "planned_spending", row["id"], int(row["estimated_amount_cents"] or amount), 70
    if not source_type:
        return
    variance = amount - expected
    db.execute(text("""INSERT INTO reconciliation_links (user_id, transaction_id, source_type, source_id, expected_amount_cents, actual_amount_cents, variance_cents, status, confidence, created_at, updated_at)
        VALUES (:user_id, :tx_id, :source_type, :source_id, :expected, :actual, :variance, :status, :confidence, :now, :now)"""), {"user_id": user.id, "tx_id": tx_id, "source_type": source_type, "source_id": source_id, "expected": expected, "actual": amount, "variance": variance, "status": "auto_matched" if confidence >= 80 else "suggested_match", "confidence": confidence, "now": utcnow()})
    if source_type == "bill" and confidence >= 80:
        db.execute(text("UPDATE bills SET remaining_amount_cents=0, paid_at=:now, resolved_at=:now, updated_at=:now WHERE id=:source_id AND user_id=:user_id"), {"source_id": source_id, "user_id": user.id, "now": utcnow()})


def _sync_counter(db: DbSession, connection_id: int) -> int:
    count = db.execute(text("SELECT count(*) FROM bank_sync_history WHERE bank_connection_id=:id AND status='success'"), {"id": connection_id}).scalar() or 0
    return int(count) + 1


@router.get("/providers")
def providers() -> dict[str, Any]:
    return {"providers": [{"id": MOCK_PROVIDER.provider, "name": MOCK_PROVIDER.name, "mode": "mock", "institutions": MOCK_PROVIDER.institutions()}]}


@router.get("")
def list_connections(db: DbSession = DB, current_user: User = USER) -> list[dict[str, Any]]:
    ensure_banking_schema(db)
    rows = db.execute(text("SELECT * FROM bank_connections WHERE user_id=:user_id ORDER BY connected_at DESC"), {"user_id": current_user.id}).mappings().all()
    return [_connection_response(db, dict(row)) for row in rows]


@router.post("/mock/connect", status_code=status.HTTP_201_CREATED)
def connect_mock(payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_schema(db)
    provider = provider_for(payload.get("provider", MOCK_PROVIDER.provider))
    institution_id = payload.get("institution_id") or "mock-bank-au"
    institution = next((item for item in provider.institutions() if item["id"] == institution_id), provider.institutions()[0])
    connection_id_value = f"{provider.provider}:{institution_id}:{current_user.id}"
    now = utcnow()
    existing = db.execute(text("SELECT * FROM bank_connections WHERE user_id=:user_id AND provider=:provider AND provider_connection_id=:connection_id"), {"user_id": current_user.id, "provider": provider.provider, "connection_id": connection_id_value}).mappings().first()
    if existing:
        connection_id = int(existing["id"])
        db.execute(text("UPDATE bank_connections SET status='connected', error_state=NULL, updated_at=:now WHERE id=:id"), {"id": connection_id, "now": now})
    else:
        db.execute(text("""INSERT INTO bank_connections (user_id, provider, provider_connection_id, institution_id, institution_name, status, consent_status, connected_at, consent_expiry, is_mock, created_at, updated_at)
            VALUES (:user_id, :provider, :connection_id, :institution_id, :institution_name, 'connected', 'mock', :now, :expiry, 1, :now, :now)"""), {"user_id": current_user.id, "provider": provider.provider, "connection_id": connection_id_value, "institution_id": institution_id, "institution_name": institution["name"], "now": now, "expiry": (date.today() + timedelta(days=365)).isoformat()})
        connection_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    for account in provider.accounts(institution_id):
        _upsert_external_account(db, current_user, connection_id, provider.provider, account)
    db.commit()
    return _connection_response(db, _connection_row(db, current_user, connection_id))


@router.post("/{connection_id}/accounts/{external_account_id}/link")
def link_external_account(connection_id: int, external_account_id: int, payload: dict[str, Any] | None = None, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_schema(db)
    payload = payload or {}
    _connection_row(db, current_user, connection_id)
    external_account = db.execute(text("SELECT * FROM external_accounts WHERE id=:id AND user_id=:user_id AND bank_connection_id=:connection_id"), {"id": external_account_id, "user_id": current_user.id, "connection_id": connection_id}).mappings().first()
    if not external_account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="External account not found")
    external = dict(external_account)
    if payload.get("action") == "ignore":
        db.execute(text("UPDATE external_accounts SET ignored=1, status='ignored', updated_at=:now WHERE id=:id"), {"id": external_account_id, "now": utcnow()})
    else:
        fynvo_account_id = payload.get("fynvo_account_id") or external.get("fynvo_account_id") or _create_linked_account(db, current_user, external)
        _update_account_balance_metadata(db, int(fynvo_account_id), external)
        db.execute(text("UPDATE external_accounts SET fynvo_account_id=:account_id, ignored=0, status='linked', updated_at=:now WHERE id=:id"), {"account_id": fynvo_account_id, "id": external_account_id, "now": utcnow()})
    db.commit()
    row = db.execute(text("SELECT * FROM external_accounts WHERE id=:id"), {"id": external_account_id}).mappings().first()
    return _external_account_response(row)


@router.post("/{connection_id}/sync")
def sync_now(connection_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_schema(db)
    connection = _connection_row(db, current_user, connection_id)
    if connection["status"] in {"syncing", "disconnected"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connection is not available for sync")
    provider = provider_for(connection["provider"])
    started = utcnow()
    db.execute(text("UPDATE bank_connections SET status='syncing', last_attempted_sync=:now, updated_at=:now WHERE id=:id"), {"id": connection_id, "now": started})
    db.flush()
    added = updated = duplicates = ignored = 0
    sync_number = _sync_counter(db, connection_id)
    try:
        accounts = db.execute(text("SELECT * FROM external_accounts WHERE user_id=:user_id AND bank_connection_id=:connection_id AND ignored=0"), {"user_id": current_user.id, "connection_id": connection_id}).mappings().all()
        for account in accounts:
            external = dict(account)
            rows, cursor = provider.transactions(external["provider_account_id"], sync_number)
            db.execute(text("UPDATE bank_connections SET sync_cursor=:cursor WHERE id=:id"), {"cursor": cursor, "id": connection_id})
            for row in rows:
                result = _insert_or_update_transaction(db, current_user, external, row)
                if result == "added":
                    added += 1
                elif result == "updated":
                    updated += 1
                elif result == "duplicate":
                    duplicates += 1
                else:
                    ignored += 1
        completed = utcnow()
        db.execute(text("UPDATE bank_connections SET status='connected', last_successful_sync=:now, error_state=NULL, updated_at=:now WHERE id=:id"), {"id": connection_id, "now": completed})
        db.execute(text("""INSERT INTO bank_sync_history (user_id, bank_connection_id, started_at, completed_at, status, added_count, updated_count, duplicate_count, review_count, created_at)
            VALUES (:user_id, :connection_id, :started, :completed, 'success', :added, :updated, :duplicates, 0, :completed)"""), {"user_id": current_user.id, "connection_id": connection_id, "started": started, "completed": completed, "added": added, "updated": updated, "duplicates": duplicates + ignored})
        db.commit()
    except Exception as exc:
        db.execute(text("UPDATE bank_connections SET status='error', error_state=:error, updated_at=:now WHERE id=:id"), {"id": connection_id, "error": "Bank sync failed. Last-known data is still available.", "now": utcnow()})
        db.execute(text("INSERT INTO bank_sync_history (user_id, bank_connection_id, started_at, completed_at, status, error_message, created_at) VALUES (:user_id, :connection_id, :started, :completed, 'error', :error, :completed)"), {"user_id": current_user.id, "connection_id": connection_id, "started": started, "completed": utcnow(), "error": str(exc)[:500]})
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bank sync failed. Last-known data is still available.") from exc
    return {"status": "success", "added": added, "updated": updated, "duplicates_ignored": duplicates + ignored, "connection": _connection_response(db, _connection_row(db, current_user, connection_id))}


@router.post("/{connection_id}/disconnect")
def disconnect(connection_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_banking_schema(db)
    _connection_row(db, current_user, connection_id)
    db.execute(text("UPDATE bank_connections SET status='disconnected', consent_status='revoked', updated_at=:now WHERE id=:id AND user_id=:user_id"), {"id": connection_id, "user_id": current_user.id, "now": utcnow()})
    db.commit()
    return _connection_response(db, _connection_row(db, current_user, connection_id))


@router.get("/{connection_id}/sync-history")
def sync_history(connection_id: int, db: DbSession = DB, current_user: User = USER) -> list[dict[str, Any]]:
    ensure_banking_schema(db)
    _connection_row(db, current_user, connection_id)
    rows = db.execute(text("SELECT * FROM bank_sync_history WHERE user_id=:user_id AND bank_connection_id=:connection_id ORDER BY started_at DESC LIMIT 50"), {"user_id": current_user.id, "connection_id": connection_id}).mappings().all()
    return [{"id": row["id"], "started_at": str(row["started_at"]), "completed_at": str(row["completed_at"]) if row["completed_at"] else None, "status": row["status"], "added": row["added_count"], "updated": row["updated_count"], "duplicates_ignored": row["duplicate_count"], "review_items": row["review_count"], "error_message": row["error_message"]} for row in rows]
