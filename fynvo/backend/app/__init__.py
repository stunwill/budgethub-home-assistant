"""Fynvo application package.

v0.12.0 keeps the stable v09 API wiring and attaches the v0.12 dashboard,
Goals and Bank Connections through the existing `/api` router.
"""

from . import banking_v12, dashboard_v12, goals, v09

v09.router.include_router(dashboard_v12.router)
v09.router.include_router(goals.router)
v09.router.include_router(banking_v12.router)
