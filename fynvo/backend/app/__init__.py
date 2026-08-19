"""Fynvo application package.

v1.0.0 keeps the proven v0.x services in place and layers stable-production
reference-data, card, recurring-payment and migration behaviour on top of them.
"""

from . import budget, database, finance, forecast, schemas, v1

# Preserve the v0.17 migration chain, then run the forward-only v1 migration.
_legacy_run_migrations = database.run_migrations


def _run_migrations_v1() -> None:
    _legacy_run_migrations()
    v1.run_v1_migrations(database.get_engine())


database.run_migrations = _run_migrations_v1

# Main imports these names after package initialisation, so patching the existing
# modules avoids a broad route/API rewrite while making v1 behaviour authoritative.
schemas.RecurringExpenseCreate = v1.RecurringExpenseCreateV1
finance.create_recurring = v1.create_recurring_v1
finance.list_recurring = v1.list_recurring_v1
finance.recurring_response = v1.recurring_response
finance.schedule_events = v1.schedule_events_v1

_legacy_ensure_seed_data = finance.ensure_seed_data


def _ensure_seed_data_v1(db, user) -> None:
    v1.ensure_reference_data(db, user)
    _legacy_ensure_seed_data(db, user)


finance.ensure_seed_data = _ensure_seed_data_v1

budget.list_categories = v1.list_categories_v1
budget.create_category = v1.create_category_v1
budget.update_category = v1.update_category_v1
forecast._recurring_events = v1.forecast_recurring_events_v1

# Import route modules only after the compatibility patches above. v09 binds
# category and recurring helpers at import time.
from . import (
    auth_v15,
    banking_v12,
    budget_v14,
    dashboard_v12,
    goals,
    insights_v14,
    scenarios,
    v09,
)

# Replace legacy routes whose implementations are superseded by authoritative
# v1 behaviour. Keep the existing URLs so bookmarks and integrations continue
# to work across the stable upgrade.
v09.router.routes = [
    route
    for route in v09.router.routes
    if not (
        getattr(route, "path", None) == "/api/budgets/analysis"
        or (
            getattr(route, "path", None) == "/api/recurring-expenses/{expense_id}"
            and "PUT" in getattr(route, "methods", set())
        )
    )
]
v09.router.include_router(budget_v14.router)
v09.router.include_router(v1.router)
v09.router.include_router(auth_v15.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
v09.router.include_router(insights_v14.router)
