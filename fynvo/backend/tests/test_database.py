from app.database import get_engine, run_migrations
from sqlalchemy import text


def test_database_migration_records_schema_version(client):
    run_migrations()
    with get_engine().connect() as connection:
        version = connection.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
    assert version == 1
