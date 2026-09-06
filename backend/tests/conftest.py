from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles

from app import main


@pytest.fixture(autouse=True)
def no_live_semantics(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)


@pytest.fixture
def client(tmp_path, monkeypatch):
    for name in ('UPLOADS', 'EVIDENCE', 'REPORTS', 'DISCOVER_REPORTS'):
        path = tmp_path / name.lower()
        path.mkdir()
        monkeypatch.setattr(main, name, path)
    mount = next(route for route in main.app.routes if route.path == '/evidence')
    monkeypatch.setattr(mount, 'app', StaticFiles(directory=main.EVIDENCE))
    with TestClient(main.app) as client:
        yield client


@pytest.fixture(scope='session')
def sample():
    return Path(__file__).resolve().parents[2] / 'sample'
