import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

APP_VERSION = "0.3.0"


class Settings(BaseModel):
    data_dir: Path
    database_url: str
    timezone: str = "Australia/Melbourne"
    currency: str = "AUD"
    session_days: int = 7
    cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("FYNVO_DATA_DIR", "/data"))
    database_url = os.getenv("FYNVO_DATABASE_URL", f"sqlite:///{data_dir / 'fynvo.sqlite3'}")
    cookie_secure = os.getenv("FYNVO_COOKIE_SECURE", "false").lower() == "true"
    return Settings(data_dir=data_dir, database_url=database_url, cookie_secure=cookie_secure)
