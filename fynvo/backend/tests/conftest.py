import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FYNVO_DATA_DIR", str(tmp_path))
    from app.config import get_settings
    from app.database import reset_database_for_tests

    reset_database_for_tests()
    get_settings.cache_clear()
    import app.main as main_module

    importlib.reload(main_module)
    with TestClient(main_module.app) as test_client:
        # The v1.2 household schema is layered on top of the existing migration
        # runner. Run it explicitly for each freshly reset test database so
        # every test starts with the same schema as a production v1.2 startup.
        # This is intentionally idempotent and avoids relying on module import
        # side effects surviving importlib.reload() between tests.
        main_module.v12_mount.household._run_v12_migrations()
        yield test_client
    reset_database_for_tests()
