from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_ok():
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert "db" in body
    assert "payment_adapter" in body
    assert "courier_adapter" in body
