"""Fynvo application package.

v0.15.0 keeps the stable financial API wiring while attaching the authoritative
administrator authentication lifecycle before Home Assistant integration surfaces.
"""

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

# Replace the legacy Budget analysis route whose positional call placed `mode`
# into the `category_id` parameter. The corrected route uses explicit arguments.
v09.router.routes = [
    route
    for route in v09.router.routes
    if getattr(route, "path", None) != "/api/budgets/analysis"
]
v09.router.include_router(budget_v14.router)

v09.router.include_router(auth_v15.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
v09.router.include_router(insights_v14.router)
