from app.db import get_db
from app.services.inventory_service import InventoryException, InventoryService
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.post("/reserve")
def reserve(payload: dict, db: Session = Depends(get_db)):
    """
    payload: { "sku": "CHOC1234", "qty": 2, "ttl_seconds": 900 }
    returns reservation record
    """
    sku = payload.get("sku")
    qty = int(payload.get("qty", 0))
    ttl = payload.get("ttl_seconds")
    svc = InventoryService(db)
    try:
        r = svc.reserve(sku, qty, ttl_seconds=ttl)
        return {
            "reservation_id": r.id,
            "sku": r.sku,
            "qty": r.quantity,
            "reserved_until": r.reserved_until.isoformat(),
        }
    except InventoryException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/release")
def release(payload: dict, db: Session = Depends(get_db)):
    """
    payload: { "reservation_id": 1 }
    """
    rid = int(payload.get("reservation_id"))
    svc = InventoryService(db)
    try:
        r = svc.release(rid)
        return {"reservation_id": r.id, "status": r.status}
    except InventoryException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/commit")
def commit(payload: dict, db: Session = Depends(get_db)):
    """
    payload: { "reservation_id": 1, "order_id": 42 }
    """
    rid = int(payload.get("reservation_id"))
    order_id = payload.get("order_id")
    svc = InventoryService(db)
    try:
        r = svc.commit(rid, order_id=order_id)
        return {"reservation_id": r.id, "status": r.status}
    except InventoryException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/available/{sku}")
def available(sku: str, db: Session = Depends(get_db)):
    svc = InventoryService(db)
    try:
        avail = svc.available_quantity(sku)
        return {"sku": sku, "available": avail}
    except InventoryException as e:
        raise HTTPException(status_code=404, detail=str(e))
