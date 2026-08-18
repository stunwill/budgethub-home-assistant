"""Fynvo application package.

v0.14.0 keeps the stable v09 API wiring while attaching the current authentication,
dashboard, Goals, Bank Connections, Scenario and Insights services through the existing
`/api` router.
"""

from . import (
    auth_v13,
    banking_v12,
    budget_v14,
    dashboard_v12,
    goals,
    insights_v14,
    scenarios,
    v09,
)

# Replace the legacy Budget analysis route whose positional call placed `mode`
# into the `category_id` parameter. The corrected v0.14 route uses explicit
# keyword arguments and therefore stays consistent with the Insights service.
v09.router.routes = [
    route
    for route in v09.router.routes
    if getattr(route, "path", None) != "/api/budgets/analysis"
]
v09.router.include_router(budget_v14.router)

v09.router.include_router(auth_v13.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
v09.router.include_router(insights_v14.router)
