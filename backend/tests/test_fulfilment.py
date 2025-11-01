from app.db import init_db, SessionLocal
from app.models.product import Product
from app.services.fulfilment_service import FulfilmentService
from app.services.order_service import OrderService
from app.repositories.idempotency_repo import IdempotencyRepository
from app.adapters.mock_courier import MockCourierAdapter

def setup_module(module):
    init_db()
    db = SessionLocal()
    try:
        db.add(Product(sku="PKG1", name="PackItem", price_cents=100, stock=5))
        db.commit()
    finally:
        db.close()

def test_packing_task_created_after_order():
    db = SessionLocal()
    try:
        order_svc = OrderService(db)
        resp = order_svc.create_order(None, [{"sku":"PKG1","qty":1}], {"token":"tok-1"}, idempotency_key="ftest-1")
        # After creation, a packing task should exist
        fulfil = FulfilmentService(db)
        tasks = fulfil.list_pending_tasks()
        assert any(t.order_id == resp["orderId"] for t in tasks)
    finally:
        db.close()

def test_mark_packed_and_book():
    db = SessionLocal()
    try:
        fulfil = FulfilmentService(db, courier_adapter=MockCourierAdapter(delay_ms=1))
        # create temporary task
        t = fulfil.create_packing_task_for_order(1)
        shipment = fulfil.mark_packed_and_book(t.id)
        assert shipment.tracking_number.startswith("TRK-") or shipment.courier == "mock-courier"
    finally:
        db.close()
