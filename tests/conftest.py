import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)
