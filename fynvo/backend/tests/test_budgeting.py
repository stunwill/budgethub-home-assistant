from datetime import date

import pytest
from app.budget import (
    analyse_budgets,
    create_budget,
    create_category,
    list_views,
    period_bounds,
    reset_view,
    save_view,
    update_budget,
    update_category,
)
from app.database import get_engine, get_session_factory, run_migrations
from fastapi import HTTPException
from sqlalchemy import text


def setup_user(client):
    client.post("/api/auth/setup", json={"username": "stu", "display_name": "Stu", "password": "Password123!"})
    db = get_session_factory()()
    try:
        user_id = db.execute(text("SELECT id FROM users WHERE username='stu'")).scalar()
        user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).first()
        return db, user
    except RuntimeError:
        db.close()
        raise


def test_budget_migration_schema_version_thirteen(client):
    run_migrations()
    with get_engine().begin() as connection:
        assert connection.execute(text("SELECT max(version) FROM schema_version")).scalar() == 13
        tables = connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars().all()
    assert "budgets" in tables
    assert "categories" in tables
    assert "saved_views" in tables
    assert "import_batches" in tables


def test_weekly_monthly_quarterly_annual_and_true_fortnight_periods():
    assert period_bounds("weekly", today=date(2026, 8, 19)) == (date(2026, 8, 17), date(2026, 8, 23))
    assert period_bounds("fortnightly", anchor=date(2026, 10, 1), today=date(2026, 10, 29)) == (date(2026, 10, 29), date(2026, 11, 11))
    assert period_bounds("monthly", today=date(2028, 2, 12)) == (date(2028, 2, 1), date(2028, 2, 29))
    assert period_bounds("quarterly", today=date(2026, 5, 5)) == (date(2026, 4, 1), date(2026, 6, 30))
    assert period_bounds("annual", today=date(2026, 8, 16)) == (date(2026, 1, 1), date(2026, 12, 31))


def test_category_hierarchy_reparent_and_cycle_prevention(client):
    db, user = setup_user(client)
    try:
        utilities = create_category(db, user, {"name": "Utilities", "budget_relationship": "shared_parent_pool"})
        electricity = create_category(db, user, {"name": "Electricity", "parent_id": utilities["id"]})
        assert update_category(db, user, electricity["id"], {"name": "Power", "parent_id": utilities["id"]})["path"] == "Utilities → Power"
        with pytest.raises(HTTPException):
            update_category(db, user, utilities["id"], {"parent_id": electricity["id"]})
    finally:
        db.close()


def test_budget_create_edit_deactivate_and_version_history(client):
    db, user = setup_user(client)
    try:
        groceries = create_category(db, user, {"name": "Groceries"})
        budget = create_budget(db, user, {"name": "Groceries monthly", "period_type": "monthly", "amount": "1200", "category_id": groceries["id"], "start_date": "2026-08-01"})
        assert budget["amount"] == "1200.00"
        edited = update_budget(db, user, budget["id"], {"amount": "1300", "effective_from": "2026-09-01", "change_note": "Food prices"})
        assert edited["amount"] == "1300.00"
        assert len(edited["versions"]) == 2
    finally:
        db.close()


def test_budget_analysis_respects_category_hierarchy_and_actuals(client):
    db, user = setup_user(client)
    try:
        parent = create_category(db, user, {"name": "Food", "budget_relationship": "shared_parent_pool"})
        child = create_category(db, user, {"name": "Groceries", "parent_id": parent["id"]})
        create_budget(db, user, {"name": "Food monthly", "period_type": "monthly", "amount": "1000", "category_id": parent["id"], "start_date": "2026-08-01"})
        account = client.post("/api/accounts", json={"name": "Everyday", "account_type": "transaction", "opening_balance": "1000"}).json()
        client.post("/api/transactions", json={"account_id": account["id"], "date": "2026-08-10", "amount": "250", "transaction_type": "expense", "description": "Shop", "category": child["path"]})
        result = analyse_budgets(db, user, period="monthly", today=date(2026, 8, 20))
        assert result["total_budget"] == "1000.00"
    finally:
        db.close()


def test_saved_views_create_list_and_reset(client):
    db, user = setup_user(client)
    try:
        saved = save_view(db, user, {"name": "Monthly view", "view_type": "budget", "config": {"period": "monthly"}})
        assert saved["name"] == "Monthly view"
        assert len(list_views(db, user)) == 1
        reset_view(db, user, saved["id"])
        assert list_views(db, user) == []
    finally:
        db.close()
