from __future__ import annotations

import secrets
import string
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import database as database_module
from .auth import get_current_user, revoke_user_sessions
from .database import get_db
from .models import User
from .security import hash_password, utcnow

router = APIRouter(prefix="/api/household", tags=["household"])
DB = Depends(get_db)
USER = Depends(get_current_user)
ROLES = {"administrator", "household_member", "read_only"}
VISIBILITIES = {"household_shared", "private"}


def _has_column(connection, table: str, column: str) -> bool:
    rows = connection.execute(text(f"PRAGMA table_info({table})")).mappings().all()
    return any(row["name"] == column for row in rows)


def _run_v12_migrations() -> None:
    engine = database_module.get_engine()
    now = utcnow()
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS households (
                id INTEGER PRIMARY KEY,
                name VARCHAR(160) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                timezone VARCHAR(80) NOT NULL DEFAULT 'Australia/Melbourne',
                currency VARCHAR(8) NOT NULL DEFAULT 'AUD',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS household_memberships (
                id INTEGER PRIMARY KEY,
                household_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role VARCHAR(40) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                joined_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                deactivated_at DATETIME,
                UNIQUE(household_id, user_id),
                FOREIGN KEY(household_id) REFERENCES households(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS record_ownership (
                id INTEGER PRIMARY KEY,
                household_id INTEGER NOT NULL,
                record_type VARCHAR(60) NOT NULL,
                record_id INTEGER NOT NULL,
                owner_user_id INTEGER,
                visibility VARCHAR(30) NOT NULL DEFAULT 'household_shared',
                created_by_user_id INTEGER,
                updated_by_user_id INTEGER,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(record_type, record_id),
                FOREIGN KEY(household_id) REFERENCES households(id),
                FOREIGN KEY(owner_user_id) REFERENCES users(id),
                FOREIGN KEY(created_by_user_id) REFERENCES users(id),
                FOREIGN KEY(updated_by_user_id) REFERENCES users(id)
            )
        """))
        if not _has_column(connection, "users", "must_change_password"):
            connection.execute(text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"))
        if not _has_column(connection, "users", "last_login_at"):
            connection.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))

        household_id = connection.execute(text("SELECT id FROM households ORDER BY id LIMIT 1")).scalar()
        if household_id is None:
            connection.execute(text("""
                INSERT INTO households(name, status, timezone, currency, created_at, updated_at)
                VALUES ('Fynvo Household', 'active', 'Australia/Melbourne', 'AUD', :now, :now)
            """), {"now": now})
            household_id = int(connection.execute(text("SELECT last_insert_rowid()")).scalar())

        users = connection.execute(text("SELECT id, is_admin, is_active FROM users ORDER BY id")).mappings().all()
        for row in users:
            existing = connection.execute(text("""
                SELECT id FROM household_memberships WHERE household_id=:household AND user_id=:user
            """), {"household": household_id, "user": row["id"]}).scalar()
            if existing is None:
                role = "administrator" if bool(row["is_admin"]) else "household_member"
                member_status = "active" if bool(row["is_active"]) else "inactive"
                connection.execute(text("""
                    INSERT INTO household_memberships(
                        household_id, user_id, role, status, joined_at, updated_at, deactivated_at
                    ) VALUES (
                        :household, :user, :role, :status, :now, :now, :deactivated
                    )
                """), {
                    "household": household_id,
                    "user": row["id"],
                    "role": role,
                    "status": member_status,
                    "now": now,
                    "deactivated": None if member_status == "active" else now,
                })

        record_tables = {
            "account": "accounts",
            "transaction": "transactions",
            "transfer": "transfers",
            "income": "income_sources",
            "recurring_expense": "recurring_expenses",
            "bill": "bills",
            "planned_spending": "planned_spending",
            "category": "categories",
            "budget": "budgets",
            "goal": "goals",
            "scenario": "scenarios",
            "insight": "insights",
            "import_batch": "import_batches",
        }
        existing_tables = {
            row["name"] for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).mappings()
        }
        for record_type, table in record_tables.items():
            if table not in existing_tables:
                continue
            cols = {row["name"] for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()}
            if "user_id" not in cols:
                continue
            connection.execute(text(f"""
                INSERT OR IGNORE INTO record_ownership(
                    household_id, record_type, record_id, owner_user_id, visibility,
                    created_by_user_id, updated_by_user_id, created_at, updated_at
                )
                SELECT hm.household_id, :record_type, r.id, r.user_id, 'household_shared',
                       r.user_id, r.user_id, :now, :now
                FROM {table} r
                JOIN household_memberships hm ON hm.user_id=r.user_id
            """), {"record_type": record_type, "now": now})

        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_household_memberships_user ON household_memberships(user_id, status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_record_ownership_household ON record_ownership(household_id, record_type, record_id)"))
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (12)"))
        elif int(current) < 12:
            connection.execute(text("UPDATE schema_version SET version=12"))


if not getattr(database_module.run_migrations, "_fynvo_v12_household", False):
    _previous_run_migrations = database_module.run_migrations

    def _run_migrations_v12() -> None:
        _previous_run_migrations()
        _run_v12_migrations()

    _run_migrations_v12._fynvo_v12_household = True  # type: ignore[attr-defined]
    database_module.run_migrations = _run_migrations_v12


def _normalise_username(value: str) -> str:
    username = " ".join((value or "").strip().lower().split())
    if len(username) < 3 or len(username) > 64 or " " in username:
        raise HTTPException(status_code=400, detail="Username must be 3-64 characters with no spaces")
    return username


def _household_context(db: DbSession, user: User, active_only: bool = True) -> dict[str, Any]:
    status_clause = "AND hm.status='active' AND h.status='active'" if active_only else ""
    row = db.execute(text(f"""
        SELECT h.id AS household_id, h.name, h.status AS household_status, h.timezone, h.currency,
               hm.id AS membership_id, hm.role, hm.status AS membership_status
        FROM household_memberships hm
        JOIN households h ON h.id=hm.household_id
        WHERE hm.user_id=:uid {status_clause}
        ORDER BY hm.id LIMIT 1
    """), {"uid": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=403, detail="No active Household membership")
    return dict(row)


def _require_admin(db: DbSession, user: User) -> dict[str, Any]:
    context = _household_context(db, user)
    if context["role"] != "administrator":
        raise HTTPException(status_code=403, detail="Household Administrator access required")
    return context


def _active_admin_count(db: DbSession, household_id: int) -> int:
    return int(db.execute(text("""
        SELECT COUNT(*) FROM household_memberships
        WHERE household_id=:household AND role='administrator' AND status='active'
    """), {"household": household_id}).scalar() or 0)


def _temporary_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(18))


def _member_payload(row: Any) -> dict[str, Any]:
    values = dict(row)
    return {
        "membership_id": values["membership_id"],
        "user_id": values["user_id"],
        "username": values["username"],
        "display_name": values["display_name"],
        "role": values["role"],
        "status": values["membership_status"],
        "user_active": bool(values["is_active"]),
        "must_change_password": bool(values.get("must_change_password") or False),
        "mfa_enabled": bool(values.get("mfa_enabled") or False),
        "joined_at": str(values["joined_at"]),
        "deactivated_at": str(values["deactivated_at"]) if values.get("deactivated_at") else None,
        "last_login_at": str(values["last_login_at"]) if values.get("last_login_at") else None,
    }


@router.get("/current")
def current_household(current_user: User = USER, db: DbSession = DB):
    context = _household_context(db, current_user)
    member_count = db.execute(text("""
        SELECT COUNT(*) FROM household_memberships
        WHERE household_id=:household AND status='active'
    """), {"household": context["household_id"]}).scalar() or 0
    return {
        "id": context["household_id"],
        "name": context["name"],
        "status": context["household_status"],
        "timezone": context["timezone"],
        "currency": context["currency"],
        "role": context["role"],
        "member_count": int(member_count),
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
        },
    }


@router.put("/current")
def update_household(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    name = " ".join(str(payload.get("name") or "").strip().split())
    if not name or len(name) > 160:
        raise HTTPException(status_code=400, detail="Household name is required and must be 160 characters or fewer")
    db.execute(text("UPDATE households SET name=:name, updated_at=:now WHERE id=:id"), {
        "name": name,
        "now": utcnow(),
        "id": context["household_id"],
    })
    db.commit()
    return current_household(current_user, db)


@router.get("/members")
def list_members(current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    rows = db.execute(text("""
        SELECT hm.id AS membership_id, hm.role, hm.status AS membership_status,
               hm.joined_at, hm.deactivated_at, u.id AS user_id, u.username,
               u.display_name, u.is_active, u.must_change_password, u.last_login_at,
               COALESCE(ms.enabled, 0) AS mfa_enabled
        FROM household_memberships hm
        JOIN users u ON u.id=hm.user_id
        LEFT JOIN mfa_settings ms ON ms.user_id=u.id
        WHERE hm.household_id=:household
        ORDER BY CASE hm.role WHEN 'administrator' THEN 0 WHEN 'household_member' THEN 1 ELSE 2 END,
                 lower(u.display_name), u.id
    """), {"household": context["household_id"]}).mappings().all()
    return [_member_payload(row) for row in rows]


@router.post("/members", status_code=status.HTTP_201_CREATED)
def create_member(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    username = _normalise_username(str(payload.get("username") or ""))
    display_name = " ".join(str(payload.get("display_name") or "").strip().split())
    role = str(payload.get("role") or "household_member")
    if not display_name or len(display_name) > 120:
        raise HTTPException(status_code=400, detail="Display name is required")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Choose a valid Household role")
    existing = db.execute(text("SELECT id FROM users WHERE lower(trim(username))=:username"), {"username": username}).scalar()
    if existing:
        raise HTTPException(status_code=409, detail="That username is already in use")
    password = str(payload.get("temporary_password") or "") or _temporary_password()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Temporary password must be at least 8 characters")
    now = utcnow()
    db.execute(text("""
        INSERT INTO users(username, display_name, password_hash, is_admin, is_active,
                          must_change_password, created_at, updated_at)
        VALUES (:username, :display_name, :password_hash, :is_admin, 1, 1, :now, :now)
    """), {
        "username": username,
        "display_name": display_name,
        "password_hash": hash_password(password),
        "is_admin": role == "administrator",
        "now": now,
    })
    user_id = int(db.execute(text("SELECT last_insert_rowid()")).scalar())
    db.execute(text("""
        INSERT INTO household_memberships(household_id, user_id, role, status, joined_at, updated_at)
        VALUES (:household, :user, :role, 'active', :now, :now)
    """), {"household": context["household_id"], "user": user_id, "role": role, "now": now})
    db.commit()
    return {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "role": role,
        "status": "active",
        "must_change_password": True,
        "temporary_password": password,
        "temporary_password_notice": "Shown once. The member must change this password after signing in.",
    }


@router.put("/members/{user_id}")
def update_member(user_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    row = db.execute(text("""
        SELECT hm.id, hm.role, hm.status, u.display_name
        FROM household_memberships hm JOIN users u ON u.id=hm.user_id
        WHERE hm.household_id=:household AND hm.user_id=:user
    """), {"household": context["household_id"], "user": user_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Household member not found")
    role = str(payload.get("role", row["role"]))
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Choose a valid Household role")
    if row["role"] == "administrator" and role != "administrator" and row["status"] == "active":
        if _active_admin_count(db, context["household_id"]) <= 1:
            raise HTTPException(status_code=409, detail="The Household must retain at least one active Administrator")
    display_name = " ".join(str(payload.get("display_name", row["display_name"]) or "").strip().split())
    if not display_name or len(display_name) > 120:
        raise HTTPException(status_code=400, detail="Display name is required")
    now = utcnow()
    db.execute(text("UPDATE users SET display_name=:name, is_admin=:admin, updated_at=:now WHERE id=:id"), {
        "name": display_name,
        "admin": role == "administrator",
        "now": now,
        "id": user_id,
    })
    db.execute(text("UPDATE household_memberships SET role=:role, updated_at=:now WHERE household_id=:household AND user_id=:user"), {
        "role": role,
        "now": now,
        "household": context["household_id"],
        "user": user_id,
    })
    db.commit()
    return {"status": "ok", "user_id": user_id, "display_name": display_name, "role": role}


@router.post("/members/{user_id}/deactivate")
def deactivate_member(user_id: int, current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    row = db.execute(text("""
        SELECT hm.role, hm.status FROM household_memberships hm
        WHERE hm.household_id=:household AND hm.user_id=:user
    """), {"household": context["household_id"], "user": user_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Household member not found")
    if row["status"] != "active":
        return {"status": "inactive", "user_id": user_id}
    if row["role"] == "administrator" and _active_admin_count(db, context["household_id"]) <= 1:
        raise HTTPException(status_code=409, detail="The Household must retain at least one active Administrator")
    now = utcnow()
    db.execute(text("UPDATE household_memberships SET status='inactive', deactivated_at=:now, updated_at=:now WHERE household_id=:household AND user_id=:user"), {
        "now": now, "household": context["household_id"], "user": user_id,
    })
    db.execute(text("UPDATE users SET is_active=0, updated_at=:now WHERE id=:user"), {"now": now, "user": user_id})
    db.commit()
    revoke_user_sessions(db, user_id)
    return {"status": "inactive", "user_id": user_id}


@router.post("/members/{user_id}/reactivate")
def reactivate_member(user_id: int, current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    exists = db.execute(text("SELECT id FROM household_memberships WHERE household_id=:household AND user_id=:user"), {
        "household": context["household_id"], "user": user_id,
    }).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Household member not found")
    now = utcnow()
    db.execute(text("UPDATE household_memberships SET status='active', deactivated_at=NULL, updated_at=:now WHERE household_id=:household AND user_id=:user"), {
        "now": now, "household": context["household_id"], "user": user_id,
    })
    db.execute(text("UPDATE users SET is_active=1, updated_at=:now WHERE id=:user"), {"now": now, "user": user_id})
    db.commit()
    return {"status": "active", "user_id": user_id}


@router.post("/members/{user_id}/password-reset")
def reset_member_password(user_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    exists = db.execute(text("SELECT id FROM household_memberships WHERE household_id=:household AND user_id=:user"), {
        "household": context["household_id"], "user": user_id,
    }).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Household member not found")
    password = str(payload.get("temporary_password") or "") or _temporary_password()
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Temporary password must be at least 8 characters")
    db.execute(text("UPDATE users SET password_hash=:hash, must_change_password=1, updated_at=:now WHERE id=:id"), {
        "hash": hash_password(password), "now": utcnow(), "id": user_id,
    })
    db.commit()
    revoke_user_sessions(db, user_id)
    return {
        "status": "reset",
        "user_id": user_id,
        "temporary_password": password,
        "temporary_password_notice": "Shown once. The member must change this password after signing in.",
    }


@router.post("/members/{user_id}/mfa-reset")
def reset_member_mfa(user_id: int, current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    exists = db.execute(text("SELECT id FROM household_memberships WHERE household_id=:household AND user_id=:user"), {
        "household": context["household_id"], "user": user_id,
    }).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Household member not found")
    db.execute(text("DELETE FROM mfa_recovery_codes WHERE user_id=:user"), {"user": user_id})
    db.execute(text("DELETE FROM mfa_login_challenges WHERE user_id=:user"), {"user": user_id})
    db.execute(text("DELETE FROM mfa_settings WHERE user_id=:user"), {"user": user_id})
    db.commit()
    revoke_user_sessions(db, user_id)
    return {"status": "reset", "user_id": user_id}


@router.post("/members/{user_id}/sessions/revoke")
def revoke_member_sessions(user_id: int, current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    exists = db.execute(text("SELECT id FROM household_memberships WHERE household_id=:household AND user_id=:user"), {
        "household": context["household_id"], "user": user_id,
    }).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Household member not found")
    count = revoke_user_sessions(db, user_id)
    return {"status": "ok", "user_id": user_id, "revoked_sessions": count}


@router.get("/ownership/accounts/{account_id}")
def account_ownership(account_id: int, current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    row = db.execute(text("""
        SELECT ro.*, a.name AS account_name, u.display_name AS owner_name
        FROM record_ownership ro
        JOIN accounts a ON a.id=ro.record_id
        LEFT JOIN users u ON u.id=ro.owner_user_id
        WHERE ro.household_id=:household AND ro.record_type='account' AND ro.record_id=:record
    """), {"household": context["household_id"], "record": account_id}).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Account ownership metadata not found")
    return dict(row)


@router.put("/ownership/accounts/{account_id}")
def update_account_ownership(account_id: int, payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    context = _require_admin(db, current_user)
    visibility = str(payload.get("visibility") or "household_shared")
    owner_user_id = payload.get("owner_user_id")
    if visibility not in VISIBILITIES:
        raise HTTPException(status_code=400, detail="Choose a valid visibility")
    if owner_user_id not in (None, ""):
        owner_user_id = int(owner_user_id)
        valid_owner = db.execute(text("""
            SELECT id FROM household_memberships
            WHERE household_id=:household AND user_id=:user AND status='active'
        """), {"household": context["household_id"], "user": owner_user_id}).scalar()
        if not valid_owner:
            raise HTTPException(status_code=400, detail="Choose an active Household member as owner")
    else:
        owner_user_id = None
    exists = db.execute(text("SELECT id FROM accounts WHERE id=:id"), {"id": account_id}).scalar()
    if not exists:
        raise HTTPException(status_code=404, detail="Account not found")
    now = utcnow()
    db.execute(text("""
        INSERT INTO record_ownership(
            household_id, record_type, record_id, owner_user_id, visibility,
            created_by_user_id, updated_by_user_id, created_at, updated_at
        ) VALUES (
            :household, 'account', :record, :owner, :visibility, :actor, :actor, :now, :now
        )
        ON CONFLICT(record_type, record_id) DO UPDATE SET
            household_id=excluded.household_id,
            owner_user_id=excluded.owner_user_id,
            visibility=excluded.visibility,
            updated_by_user_id=excluded.updated_by_user_id,
            updated_at=excluded.updated_at
    """), {
        "household": context["household_id"], "record": account_id,
        "owner": owner_user_id, "visibility": visibility,
        "actor": current_user.id, "now": now,
    })
    db.commit()
    return account_ownership(account_id, current_user, db)


@router.post("/me/change-temporary-password")
def change_temporary_password(payload: dict[str, Any], current_user: User = USER, db: DbSession = DB):
    new_password = str(payload.get("new_password") or "")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    db.execute(text("UPDATE users SET password_hash=:hash, must_change_password=0, updated_at=:now WHERE id=:id"), {
        "hash": hash_password(new_password), "now": utcnow(), "id": current_user.id,
    })
    db.commit()
    revoke_user_sessions(db, current_user.id)
    return {"status": "changed", "reauthentication_required": True}
