from app.adapters.mock_courier import MockCourierAdapter
from app.adapters.mock_payment import MockPaymentAdapter
from app.db import SessionLocal, engine
from app.repositories.idempotency_repo import IdempotencyRepository
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/health", tags=["health"])
def health():
    db_ok = False
    payment_ok = False
    courier_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    db = SessionLocal()
    try:
        # Instantiate the required repository
        idem_repo = IdempotencyRepository(db)
        # Pass the required argument to the adapter
        pay_adapter = MockPaymentAdapter(idempotency_repo=idem_repo)
        payment_ok = pay_adapter.health_check()
        courier_adapter = MockCourierAdapter()
        courier_ok = courier_adapter.health_check()
    except Exception:
        payment_ok = False
        courier_ok = False
    finally:
        db.close()

    return {
        "status": "ok" if db_ok and payment_ok and courier_ok else "degraded",
        "db": db_ok,
        "payment_adapter": payment_ok,
        "courier_adapter": courier_ok,
    }
