import os
import json
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, engine
from app.models.product import Product
from app.db import SessionLocal

client = TestClient(app)

def setup_module(module):
    # Recreate DB fresh
    init_db()

    # Seed minimal product directly for test
    db = SessionLocal()
    try:
        p = Product(sku="TEST-001", name="Test Coffee", description="Test", price_cents=499, stock=10)
        db.add(p)
        db.commit()
    finally:
        db.close()

def test_list_products():
    res = client.get("/api/products")
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert isinstance(body["items"], list)
    # Expect at least the seeded product
    skus = [it["sku"] for it in body["items"]]
    assert "TEST-001" in skus

def teardown_module(module):
    # no-op; dev DB is ephemeral for tests
    pass
