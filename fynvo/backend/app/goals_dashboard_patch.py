from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from .auth import get_current_user
from .budget import analyse_budgets
from .database import get_db
from .finance import list_bills, list_income, list_planned, list_recurring, schedule_summary, today_local
from .forecast import generate_forecast
from .goals import list_goals, ensure_goals_schema
from .intelligence import ensure_intelligence_schema
from .ledger import dashboard_position
from .models import User
from .money import cents_to_decimal, parse_money

router = APIRouter()
DB = Depends(get_db)
USER = Depends(get_current_user)


def _monthly(value_cents: int, range_days: int) -> str:
    return cents_to_decimal(round(value_cents * 30 / max(range_days, 1)))


@router.get("/dashboard/command-centre")
def command_centre_dashboard_with_intelligence_schema(
    range_days: int = Query(90, ge=7, le=365),
    db: DbSession = DB,
    current_user: User = USER,
):
    ensure_goals_schema(db)
    ensure_intelligence_schema(db)
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
    planned_cents = sum(parse_money(item["estimated_amount"]) for item in planned_period if item.get("estimated_amount"))
    income_cents = parse_money(scheduled["income"])
    commitments_cents = parse_money(scheduled["commitments"])
    return {
        "range_days": range_days,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "kpis": {
            "available_cash": position["available_cash"],
            "expected_income": scheduled["income"],
            "scheduled_commitments": scheduled["commitments"],
            "planned_spending": cents_to_decimal(planned_cents),
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
            "average_monthly_income": _monthly(income_cents, range_days),
            "average_monthly_commitments": _monthly(commitments_cents, range_days),
            "average_monthly_planned": _monthly(planned_cents, range_days),
            "average_monthly_balance": _monthly(income_cents - abs(commitments_cents), range_days),
        },
        "budget_overview": budgets.get("categories", [])[:5] if isinstance(budgets, dict) else [],
        "goals": goals[:4],
        "attention": {"suggestions": attention},
        "counts": {"bills": len(bills), "recurring": len(recurring), "income": len(income), "goals": len(goals)},
    }
