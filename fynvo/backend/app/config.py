import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

APP_VERSION = "0.5.0"


class Settings(BaseModel):
    data_dir: Path
    database_url: str
    timezone: str = "Australia/Melbourne"
    currency: str = "AUD"
    session_days: int = 7
    session_expiry_minutes: int = 60 * 24 * 7
    session_cookie_name: str = "fynvo_session"
    cookie_secure: bool = False
    max_login_attempts: int = 5
    login_attempt_window_seconds: int = 15 * 60


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data"))
    database_url = os.getenv("FYNVO_DATABASE_URL", f"sqlite:///{data_dir / 'fynvo.sqlite3'}")
    cookie_secure = os.getenv("FYNVO_COOKIE_SECURE", "false").lower() == "true"
    session_days = int(os.getenv("FYNVO_SESSION_DAYS", "7"))
    return Settings(
        data_dir=data_dir,
        database_url=database_url,
        cookie_secure=cookie_secure,
        session_days=session_days,
        session_expiry_minutes=session_days * 24 * 60,
    )
