"""Fynvo application package.

v0.12.0 keeps the stable v09 API wiring and attaches Goals, dashboard
aggregation and Bank Connections through the existing `/api` router.
"""

from . import banking_v12, goals, goals_dashboard_patch, v09

v09.router.include_router(goals_dashboard_patch.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
