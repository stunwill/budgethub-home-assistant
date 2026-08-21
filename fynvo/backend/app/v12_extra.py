from __future__ import annotations

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from . import database as database_module
from .auth import get_current_user
from .database import get_db
from .models import User
from .security import utcnow

DB = Depends(get_db)
USER = Depends(get_current_user)


def _run_v12_extra_migrations() -> None:
    engine = database_module.get_engine()
    now = utcnow()
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
    with engine.begin() as connection:
        existing_tables = {
            row["name"]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).mappings()
        }
        connection.execute(text("""
            CREATE TRIGGER IF NOT EXISTS fynvo_v12_bootstrap_user_membership
            AFTER INSERT ON users
            WHEN NOT EXISTS (SELECT 1 FROM household_memberships)
            BEGIN
                INSERT INTO household_memberships(
                    household_id, user_id, role, status, joined_at, updated_at, deactivated_at
                )
                SELECT h.id, NEW.id,
                       CASE WHEN NEW.is_admin = 1 THEN 'administrator' ELSE 'household_member' END,
                       CASE WHEN NEW.is_active = 1 THEN 'active' ELSE 'inactive' END,
                       CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                       CASE WHEN NEW.is_active = 1 THEN NULL ELSE CURRENT_TIMESTAMP END
                FROM households h
                WHERE h.status='active'
                ORDER BY h.id LIMIT 1;
            END
        """))
        for record_type, table in record_tables.items():
            if table not in existing_tables:
                continue
            columns = {
                row["name"]
                for row in connection.execute(text(f"PRAGMA table_info({table})")).mappings()
            }
            if "user_id" not in columns:
                continue
            trigger_name = f"fynvo_v12_ownership_{table}"
            connection.execute(text(f"""
                CREATE TRIGGER IF NOT EXISTS {trigger_name}
                AFTER INSERT ON {table}
                BEGIN
                    INSERT OR IGNORE INTO record_ownership(
                        household_id, record_type, record_id, owner_user_id, visibility,
                        created_by_user_id, updated_by_user_id, created_at, updated_at
                    )
                    SELECT hm.household_id, '{record_type}', NEW.id, NEW.user_id,
                           'household_shared', NEW.user_id, NEW.user_id,
                           CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM household_memberships hm
                    WHERE hm.user_id=NEW.user_id AND hm.status='active'
                    ORDER BY hm.id LIMIT 1;
                END
            """))
        connection.execute(text("""
            UPDATE record_ownership
            SET updated_at=:now
            WHERE updated_at IS NULL
        """), {"now": now})


if not getattr(database_module.run_migrations, "_fynvo_v12_extra", False):
    _previous_run_migrations = database_module.run_migrations

    def _run_migrations_v12_extra() -> None:
        _previous_run_migrations()
        _run_v12_extra_migrations()

    _run_migrations_v12_extra._fynvo_v12_extra = True  # type: ignore[attr-defined]
    database_module.run_migrations = _run_migrations_v12_extra


def my_household_security(current_user: User = USER, db: DbSession = DB):
    row = db.execute(text("""
        SELECT u.must_change_password,
               COALESCE(ms.enabled, 0) AS mfa_enabled,
               (
                   SELECT COUNT(*) FROM sessions s
                   WHERE s.user_id=u.id AND s.revoked_at IS NULL AND s.expires_at > :now
               ) AS active_session_count,
               hm.role,
               hm.status AS membership_status,
               hm.household_id
        FROM users u
        JOIN household_memberships hm ON hm.user_id=u.id
        LEFT JOIN mfa_settings ms ON ms.user_id=u.id
        WHERE u.id=:user_id AND hm.status='active'
        ORDER BY hm.id LIMIT 1
    """), {"user_id": current_user.id, "now": utcnow()}).mappings().first()
    if not row:
        return {
            "must_change_password": False,
            "mfa_enabled": False,
            "active_session_count": 0,
            "role": None,
            "membership_status": "missing",
            "household_id": None,
        }
    return {
        "must_change_password": bool(row["must_change_password"]),
        "mfa_enabled": bool(row["mfa_enabled"]),
        "active_session_count": int(row["active_session_count"] or 0),
        "role": row["role"],
        "membership_status": row["membership_status"],
        "household_id": row["household_id"],
    }
