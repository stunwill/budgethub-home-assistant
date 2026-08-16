from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
import os

APP_VERSION = "0.2.0"


class Settings(BaseModel):
    app_name: str = "Fynvo"
    app_version: str = APP_VERSION
    data_dir: Path = Path(os.getenv("FYNVO_DATA_DIR", "./data"))
    session_cookie_name: str = "fynvo_session"
    session_expiry_minutes: int = int(os.getenv("FYNVO_SESSION_EXPIRY_MINUTES", "720"))
    login_attempt_window_seconds: int = int(os.getenv("FYNVO_LOGIN_WINDOW_SECONDS", "300"))
    max_login_attempts: int = int(os.getenv("FYNVO_MAX_LOGIN_ATTEMPTS", "5"))
    default_timezone: str = os.getenv("FYNVO_TIMEZONE", "Australia/Melbourne")
    default_currency: str = os.getenv("FYNVO_CURRENCY", "AUD")

    @property
    def database_path(self) -> Path:
        return self.data_dir / "fynvo.sqlite3"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
