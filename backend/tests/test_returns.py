import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.main import app
from app.models.order import Invoice, Order, OrderLine
from app.models.product import Product

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    init_db()
    db = SessionLocal()

    # 1. Setup logic: Create data if it doesn't exist
    try:
        # Check only for the order number to see if seeding is complete
        existing_p = db.query(Product).filter(Product.sku == "RET1").first()
        if existing_p:
            p1 = existing_p
        else:
            p1 = Product(sku="RET1", name="Returnable", price_cents=500, stock=5)
            db.add(p1)
            db.commit()
            db.refresh(p1)

        # Create Order
        order = Order(
            order_number="ORD-R1", status="COMPLETED", total_cents=500, customer_id=None
        )
        db.add(order)
        db.flush()
        # OrderLine uses the correct 'price_cents' now
        ol = OrderLine(
            order_id=order.id, sku="RET1", qty=1, price_cents=500, name=p1.name
        )
        db.add(ol)
        db.flush()
        inv = Invoice(
            order_id=order.id,
            invoice_no="INV-R1",
            total_cents=500,
            tax_cents=0,
            data={"payment": {"transaction_id": "txn-test-1"}},
        )
        db.add(inv)
        db.commit()

    finally:
        db.close()

    # 2. Yield must occur once to signal fixture is ready
    yield  # Allow tests to run


def test_create_and_receive_return():
    payload = {"order_id": 1, "lines": [{"sku": "RET1", "qty": 1}]}
    r = client.post("/api/returns", json=payload)
    assert r.status_code == 200
    body = r.json()
    rma_id = body["rma_id"]

    headers = {"Idempotency-Key": "rma-key-1"}
    r2 = client.post(f"/api/returns/{rma_id}/receive", headers=headers)
    assert r2.status_code == 200
    resp = r2.json()
    assert "credit_note_id" in resp

    # product stock increased by 1
    r3 = client.get("/api/products")
    prod = next((p for p in r3.json()["items"] if p["sku"] == "RET1"), None)
    assert prod and prod["stock"] == 6


def test_idempotent_receive():
    payload = {"order_id": 1, "lines": [{"sku": "RET1", "qty": 1}]}
    r = client.post("/api/returns", json=payload)
    rma_id = r.json()["rma_id"]
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    headers = {"Idempotency-Key": "rma-key-2"}
    r2 = client.post(f"/api/returns/{rma_id}/receive", headers=headers)
    assert r2.status_code == 200
    r3 = client.post(f"/api/returns/{rma_id}/receive", headers=headers)
    assert r3.status_code == 200
    # responses should match (idempotent)
    assert r2.json() == r3.json()
