"""Fynvo application package.

v0.11.0 adds Goals through the existing v09 API router so the main FastAPI
wiring remains stable for Home Assistant ingress while new `/api/goals` and
`/api/dashboard/command-centre` endpoints are available.
"""

from . import goals, v09

v09.router.include_router(goals.router)
