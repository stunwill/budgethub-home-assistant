from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .database import get_db
from .finance import add_period
from .forecast import generate_forecast, resolve_horizon
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

SCENARIO_STATUSES = {"draft", "active", "archived"}
ADJUSTMENT_KINDS = {
    "change_recurring_expense_amount",
    "change_income_amount",
    "pause_recurring_expense",
    "stop_recurring_expense",
    "add_hypothetical_recurring_expense",
    "add_hypothetical_income",
    "one_off_expense",
    "one_off_income",
    "move_planned_spending_date",
    "change_planned_spending_amount",
}


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def ensure_scenario_schema(db: DbSession) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS scenarios (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name VARCHAR(140) NOT NULL,
            description TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            forecast_horizon VARCHAR(20) NOT NULL DEFAULT '90d',
            notes TEXT,
            created_by_user_id INTEGER,
            updated_by_user_id INTEGER,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(created_by_user_id) REFERENCES users(id),
            FOREIGN KEY(updated_by_user_id) REFERENCES users(id)
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_scenarios_user_status ON scenarios(user_id,status)"))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS scenario_adjustments (
            id INTEGER PRIMARY KEY,
            scenario_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            kind VARCHAR(60) NOT NULL,
            source_type VARCHAR(40),
            source_id INTEGER,
            name VARCHAR(180),
            amount_cents INTEGER,
            effective_from DATE,
            effective_to DATE,
            frequency VARCHAR(40),
            interval_count INTEGER,
            category VARCHAR(100),
            notes TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY(scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_scenario_adjustments_scenario ON scenario_adjustments(scenario_id)"))
    db.execute(text("CREATE INDEX IF NOT EXISTS ix_scenario_adjustments_source ON scenario_adjustments(source_type,source_id)"))
    db.commit()


def _scenario_row(db: DbSession, user: User, scenario_id: int):
    ensure_scenario_schema(db)
    row = db.execute(
        text("SELECT * FROM scenarios WHERE id=:id AND user_id=:user_id"),
        {"id": scenario_id, "user_id": user.id},
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return row


def _adjustments(db: DbSession, user: User, scenario_id: int) -> list[dict]:
    rows = db.execute(
        text("SELECT * FROM scenario_adjustments WHERE scenario_id=:scenario_id AND user_id=:user_id ORDER BY id"),
        {"scenario_id": scenario_id, "user_id": user.id},
    ).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        item["amount"] = cents_to_decimal(item["amount_cents"]) if item.get("amount_cents") is not None else None
        item["effective_from"] = _as_date(item.get("effective_from")).isoformat() if item.get("effective_from") else None
        item["effective_to"] = _as_date(item.get("effective_to")).isoformat() if item.get("effective_to") else None
        result.append(item)
    return result


def _serialize(db: DbSession, user: User, row) -> dict:
    item = dict(row)
    item["adjustments"] = _adjustments(db, user, int(item["id"]))
    return item


def _occurrence_dates(db: DbSession, user: User, source_type: str, source_id: int, start: date, end: date) -> list[date]:
    if source_type == "recurring_expense":
        table, date_col, user_col = "recurring_expenses", "next_due_date", "user_id"
    elif source_type == "income":
        table, date_col, user_col = "income_sources", "next_payment_date", "user_id"
    else:
        return []
    row = db.execute(
        text(f"SELECT {date_col} AS anchor,frequency,interval_count FROM {table} WHERE id=:id AND {user_col}=:user_id"),
        {"id": source_id, "user_id": user.id},
    ).mappings().first()
    if not row or not row["anchor"]:
        return []
    current = _as_date(row["anchor"])
    while current and current < start:
        nxt = add_period(current, row["frequency"], row["interval_count"])
        if not nxt or nxt <= current:
            return []
        current = nxt
    result = []
    while current and current <= end:
        result.append(current)
        nxt = add_period(current, row["frequency"], row["interval_count"])
        if not nxt or nxt <= current:
            break
        current = nxt
    return result


def _scenario_forecast_payload(db: DbSession, user: User, scenario: dict, horizon: str) -> dict:
    start, end, _ = resolve_horizon(horizon)
    virtual: dict[str, int] = {}
    temporary: list[dict[str, Any]] = []

    for adj in scenario["adjustments"]:
        kind = adj["kind"]
        effective_from = _as_date(adj.get("effective_from")) or start
        effective_to = _as_date(adj.get("effective_to"))
        source_type = adj.get("source_type")
        source_id = int(adj["source_id"]) if adj.get("source_id") is not None else None
        amount_cents = parse_money(adj["amount"]) if adj.get("amount") is not None else 0

        if kind in {"change_recurring_expense_amount", "change_income_amount", "pause_recurring_expense", "stop_recurring_expense"} and source_id:
            expected_type = "income" if kind == "change_income_amount" else "recurring_expense"
            dates = _occurrence_dates(db, user, expected_type, source_id, start, end)
            for when in dates:
                if when < effective_from or (effective_to and when > effective_to):
                    continue
                virtual[f"{expected_type}:{source_id}:{when.isoformat()}"] = 0 if kind in {"pause_recurring_expense", "stop_recurring_expense"} else amount_cents
            continue

        if kind == "add_hypothetical_recurring_expense":
            temporary.append({
                "kind": "recurring_expense",
                "name": adj.get("name") or "Hypothetical recurring expense",
                "amount": adj.get("amount") or "0.00",
                "start_date": effective_from.isoformat(),
                "frequency": adj.get("frequency") or "monthly",
                "interval_count": adj.get("interval_count"),
                "category": adj.get("category") or "Scenario",
            })
            continue

        if kind == "add_hypothetical_income":
            current = effective_from
            frequency = adj.get("frequency") or "monthly"
            while current and current <= end:
                if current >= start and (not effective_to or current <= effective_to):
                    temporary.append({"kind": "one_off_income", "name": adj.get("name") or "Hypothetical income", "amount": adj.get("amount") or "0.00", "date": current.isoformat(), "category": adj.get("category") or "Scenario"})
                current = add_period(current, frequency, adj.get("interval_count"))
            continue

        if kind in {"one_off_expense", "one_off_income"}:
            temporary.append({"kind": kind, "name": adj.get("name") or "Scenario adjustment", "amount": adj.get("amount") or "0.00", "date": effective_from.isoformat(), "category": adj.get("category") or "Scenario"})
            continue

        if kind in {"move_planned_spending_date", "change_planned_spending_amount"} and source_id:
            planned = db.execute(text("SELECT name,estimated_amount_cents,planned_date,category FROM planned_spending WHERE id=:id AND user_id=:user_id"), {"id": source_id, "user_id": user.id}).mappings().first()
            if not planned or planned["estimated_amount_cents"] is None or not planned["planned_date"]:
                continue
            original_amount = int(planned["estimated_amount_cents"])
            original_date = _as_date(planned["planned_date"])
            if kind == "move_planned_spending_date" and original_date:
                temporary.append({"kind": "one_off_income", "name": f"Scenario offset: {planned['name']}", "amount": cents_to_decimal(original_amount), "date": original_date.isoformat(), "category": planned["category"] or "Scenario"})
                temporary.append({"kind": "one_off_expense", "name": planned["name"], "amount": cents_to_decimal(original_amount), "date": effective_from.isoformat(), "category": planned["category"] or "Scenario"})
            elif kind == "change_planned_spending_amount" and original_date:
                delta = amount_cents - original_amount
                temporary.append({"kind": "one_off_expense", "name": f"Scenario change: {planned['name']}", "amount": cents_to_decimal(delta), "date": original_date.isoformat(), "category": planned["category"] or "Scenario"})

    return {"name": scenario["name"], "amount_changes": virtual, "adjustments": temporary}


def _comparison(db: DbSession, user: User, scenario: dict, horizon: str, mode: str = "baseline") -> dict:
    baseline = generate_forecast(db, user, horizon, mode)
    overlay = _scenario_forecast_payload(db, user, scenario, horizon)
    projected = generate_forecast(db, user, horizon, mode, scenario=overlay)
    baseline_end = parse_money(baseline["final_balance"])
    scenario_end = parse_money(projected["final_balance"])
    baseline_low = int(baseline["lowest_balance"]["balance_cents"])
    scenario_low = int(projected["lowest_balance"]["balance_cents"])
    return {
        "scenario_id": scenario["id"],
        "name": scenario["name"],
        "horizon": horizon,
        "mode": mode,
        "baseline": baseline,
        "scenario": projected,
        "difference": cents_to_decimal(scenario_end - baseline_end),
        "lowest_balance_difference": cents_to_decimal(scenario_low - baseline_low),
        "shortfall_created": baseline.get("shortfall") is None and projected.get("shortfall") is not None,
        "isolated": True,
        "explanation": "Scenario adjustments are applied only to this forecast and do not modify baseline financial records.",
    }


@router.get("/scenarios")
def list_scenarios(db: DbSession = DB, current_user: User = USER):
    ensure_scenario_schema(db)
    rows = db.execute(text("SELECT * FROM scenarios WHERE user_id=:user_id ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'draft' THEN 1 ELSE 2 END, updated_at DESC"), {"user_id": current_user.id}).mappings().all()
    return [_serialize(db, current_user, row) for row in rows]


@router.post("/scenarios", status_code=status.HTTP_201_CREATED)
def create_scenario(payload: dict[str, Any], db: DbSession = DB, current_user: User = USER):
    ensure_scenario_schema(db)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scenario name is required")
    scenario_status = str(payload.get("status") or "draft").lower()
    if scenario_status not in SCENARIO_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scenario status")
    horizon = str(payload.get("forecast_horizon") or "90d")
    resolve_horizon(horizon)
    now = utcnow()
    result = db.execute(text("INSERT INTO scenarios (user_id,name,description,status,forecast_horizon,notes,created_by_user_id,updated_by_user_id,created_at,updated_at) VALUES (:user_id,:name,:description,:status,:horizon,:notes,:created_by,:updated_by,:now,:now)"), {"user_id": current_user.id, "name": name, "description": payload.get("description"), "status": scenario_status, "horizon": horizon, "notes": payload.get("notes"), "created_by": current_user.id, "updated_by": current_user.id, "now": now})
    scenario_id = result.lastrowid
    db.commit()
    return _serialize(db, current_user, _scenario_row(db, current_user, scenario_id))


@router.put("/scenarios/{scenario_id}")
def update_scenario(scenario_id: int, payload: dict[str, Any], db: DbSession = DB, current_user: User = USER):
    row = _scenario_row(db, current_user, scenario_id)
    values = dict(row)
    for key in ("name", "description", "status", "forecast_horizon", "notes"):
        if key in payload:
            values[key] = payload[key]
    if not str(values["name"] or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Scenario name is required")
    if str(values["status"]).lower() not in SCENARIO_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid scenario status")
    resolve_horizon(str(values["forecast_horizon"]))
    db.execute(text("UPDATE scenarios SET name=:name,description=:description,status=:status,forecast_horizon=:horizon,notes=:notes,updated_by_user_id=:updated_by,updated_at=:updated_at WHERE id=:id AND user_id=:user_id"), {"name": str(values["name"]).strip(), "description": values.get("description"), "status": str(values["status"]).lower(), "horizon": values["forecast_horizon"], "notes": values.get("notes"), "updated_by": current_user.id, "updated_at": utcnow(), "id": scenario_id, "user_id": current_user.id})
    db.commit()
    return _serialize(db, current_user, _scenario_row(db, current_user, scenario_id))


@router.post("/scenarios/{scenario_id}/archive")
def archive_scenario(scenario_id: int, db: DbSession = DB, current_user: User = USER):
    _scenario_row(db, current_user, scenario_id)
    db.execute(text("UPDATE scenarios SET status='archived',updated_by_user_id=:user_id,updated_at=:now WHERE id=:id"), {"user_id": current_user.id, "now": utcnow(), "id": scenario_id})
    db.commit()
    return {"status": "ok"}


@router.post("/scenarios/{scenario_id}/adjustments", status_code=status.HTTP_201_CREATED)
def add_adjustment(scenario_id: int, payload: dict[str, Any], db: DbSession = DB, current_user: User = USER):
    _scenario_row(db, current_user, scenario_id)
    kind = str(payload.get("kind") or "")
    if kind not in ADJUSTMENT_KINDS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported scenario adjustment type")
    amount_cents = parse_money(payload.get("amount")) if payload.get("amount") not in (None, "") else None
    effective_from = _as_date(payload.get("effective_from") or payload.get("date"))
    source_id = int(payload["source_id"]) if payload.get("source_id") not in (None, "") else None
    if kind in {"one_off_expense", "one_off_income", "add_hypothetical_recurring_expense", "add_hypothetical_income", "change_recurring_expense_amount", "change_income_amount", "change_planned_spending_amount"} and amount_cents is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount is required for this adjustment")
    if kind not in {"change_planned_spending_amount"} and effective_from is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Effective date is required")
    now = utcnow()
    result = db.execute(text("INSERT INTO scenario_adjustments (scenario_id,user_id,kind,source_type,source_id,name,amount_cents,effective_from,effective_to,frequency,interval_count,category,notes,created_at,updated_at) VALUES (:scenario_id,:user_id,:kind,:source_type,:source_id,:name,:amount,:effective_from,:effective_to,:frequency,:interval_count,:category,:notes,:now,:now)"), {"scenario_id": scenario_id, "user_id": current_user.id, "kind": kind, "source_type": payload.get("source_type"), "source_id": source_id, "name": payload.get("name"), "amount": amount_cents, "effective_from": effective_from, "effective_to": _as_date(payload.get("effective_to")), "frequency": payload.get("frequency"), "interval_count": payload.get("interval_count"), "category": payload.get("category"), "notes": payload.get("notes"), "now": now})
    db.execute(text("UPDATE scenarios SET updated_by_user_id=:user_id,updated_at=:now WHERE id=:id"), {"user_id": current_user.id, "now": now, "id": scenario_id})
    adjustment_id = result.lastrowid
    db.commit()
    return next(item for item in _adjustments(db, current_user, scenario_id) if item["id"] == adjustment_id)


@router.delete("/scenarios/{scenario_id}/adjustments/{adjustment_id}")
def remove_adjustment(scenario_id: int, adjustment_id: int, db: DbSession = DB, current_user: User = USER):
    _scenario_row(db, current_user, scenario_id)
    result = db.execute(text("DELETE FROM scenario_adjustments WHERE id=:id AND scenario_id=:scenario_id AND user_id=:user_id"), {"id": adjustment_id, "scenario_id": scenario_id, "user_id": current_user.id})
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario adjustment not found")
    db.execute(text("UPDATE scenarios SET updated_by_user_id=:user_id,updated_at=:now WHERE id=:id"), {"user_id": current_user.id, "now": utcnow(), "id": scenario_id})
    db.commit()
    return {"status": "ok"}


@router.get("/scenarios/{scenario_id}/comparison")
def compare_saved_scenario(scenario_id: int, horizon: str | None = None, mode: str = "baseline", db: DbSession = DB, current_user: User = USER):
    row = _scenario_row(db, current_user, scenario_id)
    scenario = _serialize(db, current_user, row)
    selected_horizon = horizon or str(row["forecast_horizon"] or "90d")
    if mode not in {"baseline", "expected"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode must be baseline or expected")
    return _comparison(db, current_user, scenario, selected_horizon, mode)
