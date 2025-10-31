from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.order import IdempotencyRecord, IdempotencyStatus

class IdempotencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> IdempotencyRecord | None:
        return self.db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()

    def begin(self, key: str, operation: str) -> IdempotencyRecord:
        """
        Try to create an idempotency record in status IN_PROGRESS.
        If it already exists, return the existing row (caller must inspect status).
        """
        rec = IdempotencyRecord(key=key, operation=operation, status=IdempotencyStatus.IN_PROGRESS)
        try:
            self.db.add(rec)
            self.db.flush()  # will raise IntegrityError if duplicate key
            return rec
        except IntegrityError:
            self.db.rollback()  # remove partial state, keep session healthy
            existing = self.get(key)
            return existing

    def mark_completed(self, key: str, response_body: dict):
        rec = self.get(key)
        if not rec:
            raise RuntimeError("Idempotency record not found")
        rec.status = IdempotencyStatus.COMPLETED
        rec.response_body = response_body
        self.db.flush()
        return rec

    def mark_failed(self, key: str, error_message: str):
        rec = self.get(key)
        if not rec:
            # create a failed record to avoid repeated retries
            rec = IdempotencyRecord(key=key, operation="unknown", status=IdempotencyStatus.FAILED, last_error=error_message)
            self.db.add(rec)
            self.db.flush()
            return rec
        rec.status = IdempotencyStatus.FAILED
        rec.last_error = error_message
        self.db.flush()
        return rec
