from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.packing_task import PackingTask
from app.services.fulfilment_service import FulfilmentException, FulfilmentService

# from app.schemas import ( # if you have common schemas; otherwise return raw dicts)
#     PackingTaskCreate, PackingTaskUpdate, PackingTaskOut
# )

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/packing-tasks", summary="List pending packing tasks")
def list_packing_tasks(db: Session = Depends(get_db), limit: int = 100):
    svc = FulfilmentService(db)
    tasks = svc.list_pending_tasks(limit=limit)
    # return simple dicts to avoid adding new pydantic schema file
    return [
        {
            "id": t.id,
            "order_id": t.order_id,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "assigned_to": t.assigned_to,
        }
        for t in tasks
    ]


@router.post(
    "/packing-tasks/{task_id}/packed",
    summary="Mark a packing task as packed and book courier",
)
def pack_and_book(task_id: int, db: Session = Depends(get_db)):
    svc = FulfilmentService(db)
    try:
        shipment = svc.mark_packed_and_book(task_id)
        return {
            "shipment_id": shipment.id,
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
        }
    except FulfilmentException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # internal error
        raise HTTPException(status_code=500, detail="Internal error booking shipment")
