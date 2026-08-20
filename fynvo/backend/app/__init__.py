"""Fynvo application package.

v1.0.0 keeps the proven v0.x services in place and layers stable-production
reference-data, card, recurring-payment and migration behaviour on top of them.
"""

from contextvars import ContextVar

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
finance.recurring_response = v1.recurring_response

# Reference-data seeding assigns authoritative Category IDs to legacy rows. That
# migration must not also rewrite existing plain category labels such as
# "Groceries" into hierarchical display paths, because the forecast and Insights
# engines intentionally use those established labels for historical grouping.
# Explicit Category rename/move operations still synchronise denormalised labels.
_reference_seed_sync_suppressed: ContextVar[bool] = ContextVar(
    "fynvo_reference_seed_sync_suppressed",
    default=False,
)
_legacy_sync_category_denormalized_values = v1._sync_category_denormalized_values
_legacy_ensure_reference_data = v1.ensure_reference_data


def _sync_category_denormalized_values_v1(db, user) -> None:
    if _reference_seed_sync_suppressed.get():
        return
    _legacy_sync_category_denormalized_values(db, user)


def _ensure_reference_data_v1(db, user) -> None:
    token = _reference_seed_sync_suppressed.set(True)
    try:
        _legacy_ensure_reference_data(db, user)
    finally:
        _reference_seed_sync_suppressed.reset(token)


v1._sync_category_denormalized_values = _sync_category_denormalized_values_v1
v1.ensure_reference_data = _ensure_reference_data_v1

_legacy_ensure_seed_data = finance.ensure_seed_data


def _ensure_seed_data_v1(db, user) -> None:
    v1.ensure_reference_data(db, user)
    _legacy_ensure_seed_data(db, user)


finance.ensure_seed_data = _ensure_seed_data_v1

# The v1 schedule implementation is authoritative, but annual/monthly schedule
# endpoints must still honour the established household seed contract. Without
# this wrapper a fresh account could have recurring/bill seed data available via
# the recurring endpoint but missing from the annual matrix until another page
# happened to initialise it first.
def _schedule_events_v1_seeded(db, user, start, end):
    _ensure_seed_data_v1(db, user)
    return v1.schedule_events_v1(db, user, start, end)


finance.schedule_events = _schedule_events_v1_seeded

# Seed reference data only when Category-backed APIs actually need it. This keeps
# low-level legacy tests and direct service consumers free to create their own
# isolated category trees while the installed application still gets the v1
# defaults on first use.
_legacy_list_categories_v1 = v1.list_categories_v1


def _list_categories_v1_seeded(db, user):
    rows = _legacy_list_categories_v1(db, user)
    if not rows:
        v1.ensure_reference_data(db, user)
        rows = _legacy_list_categories_v1(db, user)
    return rows


v1.list_categories_v1 = _list_categories_v1_seeded
budget.list_categories = _list_categories_v1_seeded
budget.create_category = v1.create_category_v1
budget.update_category = v1.update_category_v1

# Preserve the v0.x household recurring/bill seed as part of the existing API
# contract. The v1 recurring list remains authoritative after the legacy seed is
# ensured, so existing installs and regression fixtures continue to see their
# established records.
_legacy_list_recurring_v1 = v1.list_recurring_v1


def _list_recurring_v1_seeded(db, user, filter_value="all"):
    _ensure_seed_data_v1(db, user)
    return _legacy_list_recurring_v1(db, user, filter_value)


v1.list_recurring_v1 = _list_recurring_v1_seeded
finance.list_recurring = _list_recurring_v1_seeded
forecast._recurring_events = v1.forecast_recurring_events_v1

# Import route modules only after the compatibility patches above. v09 binds
# category and recurring helpers at import time.
from . import (
    auth_v15,
    banking_v12,
    budget_v14,
    corrective_v0174,
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
v09.router.include_router(corrective_v0174.router)
