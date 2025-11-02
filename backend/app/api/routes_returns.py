from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.return_service import ReturnService, ReturnServiceException

router = APIRouter()


class ReturnLineIn(BaseModel):
    sku: str
    qty: int = 1
    reason: Optional[str] = None


class CreateReturnIn(BaseModel):
    order_id: int
    lines: List[ReturnLineIn]


@router.post("/api/returns")
def create_return(payload: CreateReturnIn, db: Session = Depends(get_db)):
    svc = ReturnService(db)
    try:
        rr = svc.create_return(payload.order_id, [l.dict() for l in payload.lines])
        return {"rma_id": rr.id, "rma_number": rr.rma_number}
    except ReturnServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/returns/{rma_id}")
def get_return(rma_id: int, db: Session = Depends(get_db)):
    svc = ReturnService(db)
    rr = svc.get_return(rma_id)
    if not rr:
        raise HTTPException(status_code=404, detail="RMA not found")
    return {
        "rma_id": rr.id,
        "rma_number": rr.rma_number,
        "order_id": rr.order_id,
        "status": rr.status,
        "lines": [{"sku": l.sku, "qty": l.qty, "reason": l.reason} for l in rr.lines],
    }


@router.post("/api/returns/{rma_id}/receive")
def receive_return(
    rma_id: int,
    request: Request,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    svc = ReturnService(db)
    try:
        resp = svc.receive_return(rma_id, idempotency_key=idempotency_key)
        return resp
    except ReturnServiceException as e:
        raise HTTPException(status_code=400, detail=str(e))
