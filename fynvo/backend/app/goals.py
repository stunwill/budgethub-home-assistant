from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .budget import analyse_budgets
from .database import get_db
from .finance import list_bills, list_income, list_planned, list_recurring, schedule_summary, today_local
from .forecast import compare_scenario, generate_forecast
from .ledger import dashboard_position
from .models import User
from .money import cents_to_decimal, parse_money
from .security import utcnow

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)

GOAL_TYPES = {"savings", "target_balance", "planned_purchase", "annual", "debt_reduction"}
GOAL_PRIORITIES = {"low", "medium", "high"}
GOAL_STATUSES = {"draft", "active", "paused", "completed", "cancelled"}
CONTRIBUTION_FREQUENCIES = {"weekly", "fortnightly", "monthly"}


def _as_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").replace(tzinfo=UTC).date()


def _money_in(value: Any | None) -> int:
    if value in (None, ""):
        return 0
    return parse_money(str(value))


def _money_out(value: int | None) -> str:
    return cents_to_decimal(value or 0)


def _now() -> datetime:
    return utcnow()


def _period_count(start: date, end: date, frequency: str) -> int:
    days = max((end - start).days, 1)
    if frequency == "weekly":
        return max(1, math.ceil(days / 7))
    if frequency == "fortnightly":
        return max(1, math.ceil(days / 14))
    return max(1, math.ceil(days / 30.4375))


def _frequency_days(frequency: str) -> int:
    if frequency == "weekly":
        return 7
    if frequency == "fortnightly":
        return 14
    return 30


def ensure_goals_schema(db: DbSession) -> None:
    with db.begin_nested():
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS financial_goals (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(140) NOT NULL,
                description TEXT,
                goal_type VARCHAR(40) NOT NULL DEFAULT 'savings',
                target_amount_cents INTEGER NOT NULL DEFAULT 0,
                current_amount_cents INTEGER NOT NULL DEFAULT 0,
                linked_category_id INTEGER,
                start_date DATE,
                target_date DATE,
                priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                contribution_frequency VARCHAR(20) NOT NULL DEFAULT 'monthly',
                contribution_amount_cents INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(40) NOT NULL DEFAULT 'active',
                notes TEXT,
                completed_at DATETIME,
                cancelled_at DATETIME,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(linked_category_id) REFERENCES categories(id)
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS goal_allocations (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                allocated_amount_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(goal_id) REFERENCES financial_goals(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS goal_contributions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_id INTEGER NOT NULL,
                transaction_id INTEGER,
                transfer_id INTEGER,
                contribution_date DATE NOT NULL,
                amount_cents INTEGER NOT NULL,
                source VARCHAR(40) NOT NULL DEFAULT 'manual',
                notes TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(goal_id) REFERENCES financial_goals(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(transfer_id) REFERENCES transfers(id)
            )
        """))
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS goal_planned_spending_links (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                goal_id INTEGER NOT NULL,
                planned_spending_id INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                UNIQUE(user_id, goal_id, planned_spending_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(goal_id) REFERENCES financial_goals(id),
                FOREIGN KEY(planned_spending_id) REFERENCES planned_spending(id)
            )
        """))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_goals_user_status ON financial_goals(user_id, status, target_date)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_goal_allocations_user_account ON goal_allocations(user_id, account_id)"))
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_goal_contributions_goal_date ON goal_contributions(goal_id, contribution_date)"))
        db.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
        current = db.execute(text("SELECT max(version) FROM schema_version")).scalar()
        if current is None:
            db.execute(text("INSERT INTO schema_version (version) VALUES (10)"))
        elif int(current) < 10:
            db.execute(text("UPDATE schema_version SET version = 10"))
    db.commit()


def _goal_row(db: DbSession, user: User, goal_id: int) -> dict[str, Any]:
    row = db.execute(text("SELECT * FROM financial_goals WHERE id = :id AND user_id = :user_id"), {"id": goal_id, "user_id": user.id}).mappings().first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return dict(row)


def _goal_amounts(db: DbSession, goal_id: int) -> dict[str, int]:
    allocation = db.execute(text("SELECT coalesce(sum(allocated_amount_cents), 0) FROM goal_allocations WHERE goal_id = :goal_id"), {"goal_id": goal_id}).scalar() or 0
    contributions = db.execute(text("SELECT coalesce(sum(amount_cents), 0) FROM goal_contributions WHERE goal_id = :goal_id"), {"goal_id": goal_id}).scalar() or 0
    return {"allocation_cents": int(allocation), "contribution_cents": int(contributions)}


def _progress(db: DbSession, goal: dict[str, Any]) -> dict[str, Any]:
    today_value = today_local()
    target = int(goal.get("target_amount_cents") or 0)
    extras = _goal_amounts(db, int(goal["id"]))
    current = int(goal.get("current_amount_cents") or 0) + extras["allocation_cents"] + extras["contribution_cents"]
    remaining = max(target - current, 0)
    pct = 100 if target <= 0 and current > 0 else round((current / target) * 100, 1) if target > 0 else 0
    target_date = _as_date(goal.get("target_date"))
    start_date = _as_date(goal.get("start_date")) or today_value
    frequency = goal.get("contribution_frequency") or "monthly"
    required = 0
    forecast_completion_date = None
    status_label = goal.get("status") or "active"
    if goal.get("status") == "completed" or current >= target > 0:
        status_label = "completed"
    elif goal.get("status") in {"cancelled", "paused", "draft"}:
        status_label = goal.get("status")
    elif target_date:
        periods = _period_count(today_value, target_date, frequency)
        required = math.ceil(remaining / periods) if remaining else 0
        expected_elapsed = max((today_value - start_date).days, 0)
        total_days = max((target_date - start_date).days, 1)
        expected_pct = min(100, round(expected_elapsed / total_days * 100, 1))
        if pct + 5 < expected_pct:
            status_label = "behind"
        elif pct > expected_pct + 5:
            status_label = "ahead"
        else:
            status_label = "on_track"
    contribution = int(goal.get("contribution_amount_cents") or 0)
    if contribution > 0 and remaining > 0:
        periods_needed = math.ceil(remaining / contribution)
        forecast_completion_date = today_value + timedelta(days=periods_needed * _frequency_days(frequency))
    elif remaining == 0:
        forecast_completion_date = today_value
    return {
        "target": _money_out(target),
        "current": _money_out(current),
        "remaining": _money_out(remaining),
        "percentage": pct,
        "required_contribution": _money_out(required),
        "current_contribution": _money_out(contribution),
        "contribution_frequency": frequency,
        "forecast_completion_date": forecast_completion_date.isoformat() if forecast_completion_date else None,
        "status": status_label,
        "allocation": _money_out(extras["allocation_cents"]),
        "contributions": _money_out(extras["contribution_cents"]),
        "explanation": f"Calculated from {_money_out(remaining)} remaining and {frequency} periods to the target date." if target_date else "Add a target date to calculate required contributions.",
    }


def _goal_response(db: DbSession, goal: dict[str, Any]) -> dict[str, Any]:
    progress = _progress(db, goal)
    return {
        "id": goal["id"],
        "name": goal["name"],
        "description": goal.get("description"),
        "goal_type": goal.get("goal_type"),
        "target_amount": _money_out(goal.get("target_amount_cents")),
        "current_amount": _money_out(goal.get("current_amount_cents")),
        "start_date": str(goal.get("start_date")) if goal.get("start_date") else None,
        "target_date": str(goal.get("target_date")) if goal.get("target_date") else None,
        "priority": goal.get("priority"),
        "contribution_frequency": goal.get("contribution_frequency"),
        "contribution_amount": _money_out(goal.get("contribution_amount_cents")),
        "status": goal.get("status"),
        "calculated_status": progress["status"],
        "notes": goal.get("notes"),
        "progress": progress,
    }


def _validate_goal(payload: dict[str, Any]) -> dict[str, Any]:
    goal_type = payload.get("goal_type", "savings")
    if goal_type not in GOAL_TYPES:
        raise HTTPException(status_code=400, detail="goal_type must be savings, target_balance, planned_purchase, annual or debt_reduction")
    priority = payload.get("priority", "medium")
    if priority not in GOAL_PRIORITIES:
        raise HTTPException(status_code=400, detail="priority must be low, medium or high")
    goal_status = payload.get("status", "active")
    if goal_status not in GOAL_STATUSES:
        raise HTTPException(status_code=400, detail="status must be draft, active, paused, completed or cancelled")
    frequency = payload.get("contribution_frequency", "monthly")
    if frequency not in CONTRIBUTION_FREQUENCIES:
        raise HTTPException(status_code=400, detail="contribution_frequency must be weekly, fortnightly or monthly")
    return {"goal_type": goal_type, "priority": priority, "status": goal_status, "frequency": frequency}


@router.get("/goals")
def list_goals(include_completed: bool = False, db: DbSession = DB, current_user: User = USER) -> list[dict[str, Any]]:
    ensure_goals_schema(db)
    rows = db.execute(text("""
        SELECT * FROM financial_goals
        WHERE user_id = :user_id AND (:include_completed = 1 OR status NOT IN ('completed', 'cancelled'))
        ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, target_date IS NULL, target_date, id
    """), {"user_id": current_user.id, "include_completed": 1 if include_completed else 0}).mappings().all()
    return [_goal_response(db, dict(row)) for row in rows]


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_goal(payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    validated = _validate_goal(payload)
    now = _now()
    result = db.execute(text("""
        INSERT INTO financial_goals (
            user_id, name, description, goal_type, target_amount_cents, current_amount_cents,
            linked_category_id, start_date, target_date, priority, contribution_frequency,
            contribution_amount_cents, status, notes, created_at, updated_at
        ) VALUES (
            :user_id, :name, :description, :goal_type, :target_amount_cents, :current_amount_cents,
            :linked_category_id, :start_date, :target_date, :priority, :frequency,
            :contribution_amount_cents, :goal_status, :notes, :created_at, :updated_at
        )
    """), {
        "user_id": current_user.id,
        "name": payload.get("name", "").strip(),
        "description": payload.get("description"),
        "goal_type": validated["goal_type"],
        "target_amount_cents": _money_in(payload.get("target_amount")),
        "current_amount_cents": _money_in(payload.get("current_amount")),
        "linked_category_id": payload.get("linked_category_id") or None,
        "start_date": _as_date(payload.get("start_date")) or today_local(),
        "target_date": _as_date(payload.get("target_date")),
        "priority": validated["priority"],
        "frequency": validated["frequency"],
        "contribution_amount_cents": _money_in(payload.get("contribution_amount")),
        "goal_status": validated["status"],
        "notes": payload.get("notes"),
        "created_at": now,
        "updated_at": now,
    })
    if not payload.get("name"):
        raise HTTPException(status_code=400, detail="Goal name is required")
    db.commit()
    return _goal_response(db, _goal_row(db, current_user, int(result.lastrowid)))


@router.get("/goals/{goal_id}")
def goal_detail(goal_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    goal = _goal_row(db, current_user, goal_id)
    allocations = db.execute(text("""
        SELECT ga.*, a.name AS account_name FROM goal_allocations ga
        JOIN accounts a ON a.id = ga.account_id
        WHERE ga.user_id = :user_id AND ga.goal_id = :goal_id
        ORDER BY ga.id
    """), {"user_id": current_user.id, "goal_id": goal_id}).mappings().all()
    contributions = db.execute(text("SELECT * FROM goal_contributions WHERE user_id = :user_id AND goal_id = :goal_id ORDER BY contribution_date DESC, id DESC"), {"user_id": current_user.id, "goal_id": goal_id}).mappings().all()
    response = _goal_response(db, goal)
    response["allocations"] = [{**dict(row), "allocated_amount": _money_out(row["allocated_amount_cents"])} for row in allocations]
    response["contributions"] = [{**dict(row), "amount": _money_out(row["amount_cents"])} for row in contributions]
    return response


@router.put("/goals/{goal_id}")
def update_goal(goal_id: int, payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    validated = _validate_goal(payload)
    db.execute(text("""
        UPDATE financial_goals SET
            name = :name, description = :description, goal_type = :goal_type,
            target_amount_cents = :target_amount_cents, current_amount_cents = :current_amount_cents,
            linked_category_id = :linked_category_id, start_date = :start_date, target_date = :target_date,
            priority = :priority, contribution_frequency = :frequency,
            contribution_amount_cents = :contribution_amount_cents, status = :goal_status,
            notes = :notes, updated_at = :updated_at
        WHERE id = :goal_id AND user_id = :user_id
    """), {
        "goal_id": goal_id,
        "user_id": current_user.id,
        "name": payload.get("name", "").strip(),
        "description": payload.get("description"),
        "goal_type": validated["goal_type"],
        "target_amount_cents": _money_in(payload.get("target_amount")),
        "current_amount_cents": _money_in(payload.get("current_amount")),
        "linked_category_id": payload.get("linked_category_id") or None,
        "start_date": _as_date(payload.get("start_date")) or today_local(),
        "target_date": _as_date(payload.get("target_date")),
        "priority": validated["priority"],
        "frequency": validated["frequency"],
        "contribution_amount_cents": _money_in(payload.get("contribution_amount")),
        "goal_status": validated["status"],
        "notes": payload.get("notes"),
        "updated_at": _now(),
    })
    db.commit()
    return _goal_response(db, _goal_row(db, current_user, goal_id))


@router.post("/goals/{goal_id}/complete")
def complete_goal(goal_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    now = _now()
    db.execute(text("UPDATE financial_goals SET status = 'completed', completed_at = :now, updated_at = :now WHERE id = :goal_id AND user_id = :user_id"), {"goal_id": goal_id, "user_id": current_user.id, "now": now})
    db.commit()
    return _goal_response(db, _goal_row(db, current_user, goal_id))


@router.post("/goals/{goal_id}/cancel")
def cancel_goal(goal_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    now = _now()
    db.execute(text("UPDATE financial_goals SET status = 'cancelled', cancelled_at = :now, updated_at = :now WHERE id = :goal_id AND user_id = :user_id"), {"goal_id": goal_id, "user_id": current_user.id, "now": now})
    db.commit()
    return _goal_response(db, _goal_row(db, current_user, goal_id))


@router.post("/goals/{goal_id}/contributions", status_code=status.HTTP_201_CREATED)
def add_contribution(goal_id: int, payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    now = _now()
    db.execute(text("""
        INSERT INTO goal_contributions (user_id, goal_id, transaction_id, transfer_id, contribution_date, amount_cents, source, notes, created_at, updated_at)
        VALUES (:user_id, :goal_id, :transaction_id, :transfer_id, :contribution_date, :amount_cents, :source, :notes, :created_at, :updated_at)
    """), {
        "user_id": current_user.id,
        "goal_id": goal_id,
        "transaction_id": payload.get("transaction_id") or None,
        "transfer_id": payload.get("transfer_id") or None,
        "contribution_date": _as_date(payload.get("date")) or today_local(),
        "amount_cents": _money_in(payload.get("amount")),
        "source": payload.get("source", "manual"),
        "notes": payload.get("notes"),
        "created_at": now,
        "updated_at": now,
    })
    db.commit()
    return goal_detail(goal_id, db, current_user)


@router.post("/goals/{goal_id}/allocations", status_code=status.HTTP_201_CREATED)
def add_allocation(goal_id: int, payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    account = db.execute(text("SELECT id FROM accounts WHERE id = :id AND user_id = :user_id"), {"id": payload.get("account_id"), "user_id": current_user.id}).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    now = _now()
    db.execute(text("""
        INSERT INTO goal_allocations (user_id, goal_id, account_id, allocated_amount_cents, notes, created_at, updated_at)
        VALUES (:user_id, :goal_id, :account_id, :amount_cents, :notes, :created_at, :updated_at)
    """), {"user_id": current_user.id, "goal_id": goal_id, "account_id": payload.get("account_id"), "amount_cents": _money_in(payload.get("amount")), "notes": payload.get("notes"), "created_at": now, "updated_at": now})
    db.commit()
    return goal_detail(goal_id, db, current_user)


@router.post("/goals/{goal_id}/planned-spending/{planned_id}")
def link_planned_spending(goal_id: int, planned_id: int, db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    _goal_row(db, current_user, goal_id)
    exists = db.execute(text("SELECT id FROM planned_spending WHERE id = :id AND user_id = :user_id"), {"id": planned_id, "user_id": current_user.id}).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Planned Spending item not found")
    db.execute(text("INSERT OR IGNORE INTO goal_planned_spending_links (user_id, goal_id, planned_spending_id, created_at) VALUES (:user_id, :goal_id, :planned_id, :created_at)"), {"user_id": current_user.id, "goal_id": goal_id, "planned_id": planned_id, "created_at": _now()})
    db.commit()
    return goal_detail(goal_id, db, current_user)


@router.post("/goals/what-if")
def goal_what_if(payload: dict[str, Any], db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    goal = _goal_row(db, current_user, int(payload.get("goal_id")))
    progress = _progress(db, goal)
    contribution_cents = _money_in(payload.get("contribution_amount"))
    remaining_cents = _money_in(progress["remaining"])
    frequency = payload.get("frequency") or goal.get("contribution_frequency") or "monthly"
    if frequency not in CONTRIBUTION_FREQUENCIES:
        raise HTTPException(status_code=400, detail="frequency must be weekly, fortnightly or monthly")
    periods = math.ceil(remaining_cents / contribution_cents) if contribution_cents > 0 else None
    completion = today_local() + timedelta(days=periods * _frequency_days(frequency)) if periods else None
    scenario = compare_scenario(db, current_user, {"adjustments": [{"label": f"Goal contribution: {goal['name']}", "amount": _money_out(-contribution_cents), "frequency": frequency}]})
    return {
        "goal_id": goal["id"],
        "contribution_amount": _money_out(contribution_cents),
        "frequency": frequency,
        "forecast_completion_date": completion.isoformat() if completion else None,
        "periods_required": periods,
        "forecast_impact": scenario,
        "explanation": "This is a what-if calculation only. It does not update the saved goal until confirmed.",
    }


@router.get("/goals/allocations/unallocated")
def unallocated_savings(db: DbSession = DB, current_user: User = USER) -> list[dict[str, Any]]:
    ensure_goals_schema(db)
    rows = db.execute(text("""
        SELECT a.id, a.name, a.account_type, a.opening_balance_cents + coalesce(sum(t.amount_cents), 0) AS balance_cents,
               coalesce((SELECT sum(allocated_amount_cents) FROM goal_allocations ga WHERE ga.account_id = a.id AND ga.user_id = :user_id), 0) AS allocated_cents
        FROM accounts a
        LEFT JOIN transactions t ON t.account_id = a.id
        WHERE a.user_id = :user_id AND a.is_active = 1 AND a.account_type IN ('transaction', 'savings', 'cash')
        GROUP BY a.id
        ORDER BY a.name
    """), {"user_id": current_user.id}).mappings().all()
    return [{"account_id": row["id"], "account_name": row["name"], "balance": _money_out(row["balance_cents"]), "allocated": _money_out(row["allocated_cents"]), "unallocated": _money_out(max(int(row["balance_cents"] or 0) - int(row["allocated_cents"] or 0), 0))} for row in rows]


@router.get("/dashboard/command-centre")
def command_centre_dashboard(range_days: int = Query(90, ge=7, le=365), db: DbSession = DB, current_user: User = USER) -> dict[str, Any]:
    ensure_goals_schema(db)
    start = today_local()
    end = start + timedelta(days=range_days)
    position = dashboard_position(db, current_user)
    scheduled = schedule_summary(db, current_user, start, end)
    forecast = generate_forecast(db, current_user, f"{range_days}d", "baseline", start)
    expected_forecast = generate_forecast(db, current_user, f"{range_days}d", "expected", start)
    bills = list_bills(db, current_user)
    recurring = list_recurring(db, current_user)
    planned = list_planned(db, current_user)
    income = list_income(db, current_user)
    budgets = analyse_budgets(db, current_user)
    goals = list_goals(False, db, current_user)
    attention = db.execute(text("SELECT count(*) FROM intelligence_suggestions WHERE user_id = :user_id AND status = 'new'"), {"user_id": current_user.id}).scalar() or 0
    commitments = [event for event in scheduled["events"] if event.get("direction") == "out" and event.get("source") in {"bill", "recurring"}]
    upcoming = scheduled["events"][:8]
    planned_period = [item for item in planned if item.get("status") not in {"cancelled"} and item.get("include_in_forecast")]
    return {
        "range_days": range_days,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "kpis": {
            "available_cash": position["available_cash"],
            "expected_income": scheduled["income"],
            "scheduled_commitments": scheduled["commitments"],
            "planned_spending": cents_to_decimal(sum(parse_money(item["estimated_amount"]) for item in planned_period if item.get("estimated_amount"))),
            "projected_balance": forecast["final_balance"],
        },
        "forecast": {
            "baseline": forecast,
            "expected": expected_forecast,
            "summary": {"baseline": forecast["final_balance"], "expected": expected_forecast["final_balance"], "lowest_balance": forecast.get("lowest_balance"), "shortfall": forecast.get("shortfall")},
        },
        "upcoming_commitments": commitments[:6],
        "upcoming": upcoming,
        "top_planned_spending": planned_period[:5],
        "quick_stats": {
            "average_monthly_income": cents_to_decimal(parse_money(scheduled["income"]) * 30 / max(range_days, 1)),
            "average_monthly_commitments": cents_to_decimal(parse_money(scheduled["commitments"]) * 30 / max(range_days, 1)),
            "average_monthly_planned": cents_to_decimal(sum(parse_money(item["estimated_amount"]) for item in planned_period if item.get("estimated_amount")) * 30 / max(range_days, 1)),
            "average_monthly_balance": cents_to_decimal((parse_money(scheduled["income"]) - abs(parse_money(scheduled["commitments"]))) * 30 / max(range_days, 1)),
        },
        "budget_overview": budgets.get("categories", [])[:5] if isinstance(budgets, dict) else [],
        "goals": goals[:4],
        "attention": {"suggestions": attention},
        "counts": {"bills": len(bills), "recurring": len(recurring), "income": len(income), "goals": len(goals)},
    }
