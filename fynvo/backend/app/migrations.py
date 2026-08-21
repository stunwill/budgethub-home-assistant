"""Explicit ordered migration orchestration for Fynvo.

This module removes release-migration ordering from Python import side effects.
Each migration body remains idempotent and forward-only.
"""

from sqlalchemy import text

from . import database, v1, v12_extra, v12_household, v13_cashflow
from .versioning import LATEST_SCHEMA_VERSION


def run_all_migrations() -> None:
    """Run Fynvo migrations in an explicit, deterministic order."""
    database.run_base_migrations()
    engine = database.get_engine()
    v1.run_v1_migrations(engine)
    database.run_v11_migrations(engine)
    v12_household._run_v12_migrations()
    v12_extra._run_v12_extra_migrations()
    v13_cashflow.run_v13_migrations(engine)
    with engine.begin() as connection:
        current = connection.execute(text("SELECT MAX(version) FROM schema_version")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version(version) VALUES (:version)"), {"version": LATEST_SCHEMA_VERSION})
        elif int(current) < LATEST_SCHEMA_VERSION:
            connection.execute(text("UPDATE schema_version SET version=:version"), {"version": LATEST_SCHEMA_VERSION})
