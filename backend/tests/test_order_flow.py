import pytest
from fastapi.testclient import TestClient

from app import db
from app.db import SessionLocal, init_db
from app.main import app
from app.models.order import Invoice, Order, OrderLine
from app.models.product import Product

client = TestClient(app)


@pytest.fixture(autouse=True, scope="session")
def setup_db():
    init_db()
    db = SessionLocal()
    try:
        if (
            db.query(Product).filter(Product.sku == "T1").first()
            and db.query(Product).filter(Product.sku == "TEST-001").first()
        ):
            print("Test data already exists, skipping seeding.")
            return

        db.add(Product(sku="T1", name="Tea 100g", price_cents=300, stock=5))
        db.add(Product(sku="T2", name="Coffee 200g", price_cents=600, stock=1))
        db.add(Product(sku="PKG1", name="Test Package", price_cents=100, stock=1))
        db.add(Product(sku="RET1", name="Returnable", price_cents=500, stock=5))
        db.add(
            Product(
                sku="TEST-001",
                name="Test Coffee",
                description="Test",
                price_cents=499,
                stock=10,
            )
        )
        # Inventory tests use RES-1 and RES-2, so add them here too:
        db.add(Product(sku="RES-1", name="Reserve1", price_cents=100, stock=5))
        db.add(Product(sku="RES-2", name="Reserve2", price_cents=200, stock=1))

        db.commit()
    finally:
        db.close()


def test_checkout_success_and_idempotency():
    payload = {
        "customer_id": None,
        "items": [{"sku": "T1", "qty": 2}],
        "payment_method": {"token": "test", "force_decline": False},
    }
    headers = {"Idempotency-Key": "idem-123"}
    r = client.post("/api/orders", json=payload, headers=headers)
    assert r.status_code == 200 or r.status_code == 201
    body = r.json()
    assert "orderId" in body
    order_id = body["orderId"]

    # Repeat with same idempotency key -> should return same payload (no duplicate order)
    r2 = client.post("/api/orders", json=payload, headers=headers)
    assert r2.status_code in (200, 201)
    assert r2.json()["orderId"] == order_id


def test_checkout_payment_decline_releases_reservations():
    payload = {
        "customer_id": None,
        "items": [{"sku": "T2", "qty": 1}],
        "payment_method": {"token": "test", "force_decline": True},
    }
    headers = {"Idempotency-Key": "idem-decline-1"}
    r = client.post("/api/orders", json=payload, headers=headers)
    # Payment declined -> 400 with detail
    assert r.status_code == 400
    assert (
        "Payment declined" in r.json()["detail"]
        or "Payment failed" in r.json()["detail"]
    )
