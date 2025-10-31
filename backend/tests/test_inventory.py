import time
from fastapi.testclient import TestClient
from app.main import app
from app.db import init_db, SessionLocal
from app.models.product import Product
from app.services.inventory_service import InventoryService, InventoryException
from sqlalchemy.orm import sessionmaker

client = TestClient(app)

def setup_module(module):
    init_db()
    # Use the normal session for setup, but explicitly commit
    db = SessionLocal() 
    try:
        db.add(Product(sku="RES-1", name="Reserve1", price_cents=100, stock=5))
        db.add(Product(sku="RES-2", name="Reserve2", price_cents=200, stock=1))
        db.commit() # Explicit commit needed here
    finally:
        db.close()

def test_reserve_and_commit():
    db = SessionLocal()
    try:
        svc = InventoryService(db)
        with db.begin():
            r = svc.reserve("RES-1", 2, ttl_seconds=30)
            assert r.quantity == 2
            
        # NOTE: svc.commit() must handle its own transaction (with db.begin()) internally
        # commit
        committed = svc.commit(r.id, order_id=999)
        assert committed.status == "committed"
        
        db.refresh(db.query(Product).filter(Product.sku == "RES-1").first())
        # product stock decreased
        prod = db.query(Product).filter(Product.sku == "RES-1").first()
        assert prod.stock == 3
    finally:
        db.close()

def test_reserve_release():
    db = SessionLocal()
    try:
        svc = InventoryService(db)
        with db.begin():
            r = svc.reserve("RES-1", 1, ttl_seconds=30)
            assert r.status == "reserved"
        
        # NOTE: svc.release() must handle its own transaction internally
        released = svc.release(r.id)
        assert released.status == "released"
    finally:
        db.close()

def test_ttl_expiry():
    db = SessionLocal()
    try:
        svc = InventoryService(db)
        with db.begin():
            r = svc.reserve("RES-2", 1, ttl_seconds=1) # tiny TTL
            assert r.status == "reserved"
        
        # wait for TTL
        time.sleep(1.5)
        
        # NOTE: svc.expire_overdue() must handle its own transaction internally
        expired_ids = svc.expire_overdue()
        assert r.id in expired_ids
    finally:
        db.close()
