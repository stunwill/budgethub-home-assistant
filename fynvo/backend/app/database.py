from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    from .models import AppConfig, LoginAttempt, Session, User

    engine = get_engine()
    Base.metadata.create_all(bind=engine, tables=[
        User.__table__,
        Session.__table__,
        LoginAttempt.__table__,
        AppConfig.__table__,
    ])
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
        current = connection.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version (version) VALUES (1)"))
        elif current < 1:
            connection.execute(text("UPDATE schema_version SET version = 1"))


def reset_database_for_tests() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        Base.metadata.drop_all(bind=_engine)
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()
