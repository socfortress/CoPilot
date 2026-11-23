import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from runner.compliance import clear_cache
from runner.main import create_app
from runner.settings import Settings
from tests.support import FAKES
from tests.support import FIXTURES
from tests.support import TOKEN


@pytest.fixture(autouse=True)
def _fresh_catalog_cache():
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        token=TOKEN,
        prowler_cmd=(sys.executable, str(FAKES / "fake_prowler.py")),
        prowler_python_cmd=(sys.executable,),
        compliance_dir=FIXTURES / "compliance",
        work_dir=tmp_path / "work",
        max_concurrent=2,
        scan_timeout=60,
        connection_test_timeout=20,
        normalize_timeout=60,
        job_ttl=3600,
        max_jobs=50,
        scan_home=str(tmp_path),
        scan_path="/usr/bin:/bin",
        passthrough_env={"FAKE_RECORD_DIR": str(tmp_path)},
    )


@pytest.fixture
def make_client():
    clients = []

    def make(settings: Settings, helper: Path | None = FAKES / "fake_connection_helper.py", authorized: bool = True) -> TestClient:
        app = create_app(settings)
        if helper is not None:
            app.state.connections.helper = helper
        client = TestClient(app)
        client.__enter__()
        clients.append(client)
        if authorized:
            client.headers["Authorization"] = f"Bearer {TOKEN}"
        return client

    yield make
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client, settings) -> TestClient:
    return make_client(settings)
