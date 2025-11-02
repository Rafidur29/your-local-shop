from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import PackingTask


router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/packing-tasks")
def list_packing_tasks(db: Session = Depends(get_db)):
    tasks = db.query(PackingTask).filter_by(status="PENDING").all()
    return [
        {
            "id": t.id,
            "order_id": t.order_id,
            "sku": t.sku,
            "qty": t.qty,
            "status": t.status,
        }
        for t in tasks
    ]


@router.post("/packing-tasks/{task_id}/packed")
def mark_packed(task_id: int, db: Session = Depends(get_db)):
    t = db.query(PackingTask).filter_by(id=task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    t.status = "PACKED"
    db.commit()
    # (Chung webhook could book courier next)
    return {"ok": True}
