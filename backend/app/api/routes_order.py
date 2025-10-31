from fastapi import APIRouter, Depends, Header, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.order_service import OrderService, OrderServiceException

router = APIRouter(tags=["orders"])

class OrderItemIn(BaseModel):
    sku: str
    qty: int = Field(..., gt=0)

class CreateOrderIn(BaseModel):
    customer_id: Optional[int] = None
    items: List[OrderItemIn]
    payment_method: dict  # for mock, accept free-form dict

@router.post("", summary="Create order (checkout)")
def create_order(payload: CreateOrderIn, db: Session = Depends(get_db), idempotency_key: Optional[str] = Header(None, convert_underscores=False)):
    svc = OrderService(db)
    try:
        resp = svc.create_order(payload.customer_id, [it.dict() for it in payload.items], payload.payment_method, idempotency_key=idempotency_key)
        return resp
    except OrderServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"CRITICAL ERROR: {type(e).__name__}: {str(e)}") # Add logging to console
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")
