from fastapi import APIRouter
from sqlalchemy import text
from app.db import engine
from app.adapters.mock_payment import MockPaymentAdapter
from app.adapters.mock_courier import MockCourierAdapter

router = APIRouter(prefix="/api")

@router.get("/health", tags=["health"])
def health():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    pay_adapter = MockPaymentAdapter()
    courier_adapter = MockCourierAdapter()
    return {
        "status": "ok" if db_ok and pay_adapter.is_available() and courier_adapter.is_available() else "degraded",
        "db": db_ok,
        "payment_adapter": pay_adapter.is_available(),
        "courier_adapter": courier_adapter.is_available(),
    }
