"""Fynvo application package.

v0.14.0 keeps the stable v09 API wiring while attaching the current authentication,
dashboard, Goals, Bank Connections, Scenario and Insights services through the existing
`/api` router.
"""

from . import auth_v13, banking_v12, dashboard_v12, goals, insights, scenarios, v09

v09.router.include_router(auth_v13.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
v09.router.include_router(insights.router)
