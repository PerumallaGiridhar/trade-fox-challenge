import pytest
from fastapi.testclient import TestClient

from main import app
from app.routes import engine


@pytest.fixture(autouse=True)
def reset_engine_state():
    engine.trades.clear()
    if hasattr(engine, "_trade_counter"):
        engine._trade_counter = 1
    yield
    engine.trades.clear()
    if hasattr(engine, "_trade_counter"):
        engine._trade_counter = 1


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client