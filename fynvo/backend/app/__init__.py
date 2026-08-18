"""Fynvo application package.

v0.13.0 keeps the stable v09 API wiring while attaching the current authentication,
dashboard, Goals, Bank Connections and Scenario services through the existing `/api` router.
"""

from . import auth_v13, banking_v12, dashboard_v12, goals, scenarios, v09

v09.router.include_router(auth_v13.router)
v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
v09.router.include_router(scenarios.router)
