from app.db import SessionLocal, init_db
from app.main import app
from app.models.product import Product
from fastapi.testclient import TestClient

client = TestClient(app)

# def setup_module(module):
#     init_db()
#     db = SessionLocal()
#     try:
#         db.add(Product(sku="TEST-002", name="Test Coffee", description="Test", price_cents=499, stock=10))
#         db.commit()
#     finally:
#         db.close()


def test_add_item_to_cart():
    res = client.post("/api/cart/items", json={"sku": "TEST-001", "qty": 2})
    assert res.status_code == 200
    body = res.json()
    assert "cart_uuid" in body


def test_get_cart():
    res = client.get("/api/cart")
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
