from app.db import SessionLocal
from app.models import Product, ProductVariant
from app.services.inventory import InventoryService


def test_reservation_ttl_and_available_stock():
    db = SessionLocal()
    p = Product(sku="SKUX", name="Test X", price_cents=1000)
    db.add(p); db.flush()
    pv = ProductVariant(product_id=p.id, sku="SKUX", price_cents=1000, stock=5)
    db.add(pv); db.commit()


    inv = InventoryService(db)
    assert inv.available_stock("SKUX") == 5
    r1 = inv.reserve("SKUX", 3)
    assert inv.available_stock("SKUX") == 2
    inv.consume("SKUX", 3)
    db.close()
