from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.idempotency import IdempotencyRecord, IdempotencyStatus
from app.db import SessionLocal  # new short-lived sessions for atomic begin

class IdempotencyRepository:
    def __init__(self, db: Session):
        # db is the caller's session (longer-lived)
        self.db = db

    def get(self, key: str):
        return self.db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()

    def begin(self, key: str, operation: str) -> IdempotencyRecord:
        """
        Atomically ensure an idempotency row exists.
        This uses a short-lived SessionLocal() to INSERT+COMMIT the IN_PROGRESS marker,
        guaranteeing visibility to other concurrent requests immediately.
        Returns the IdempotencyRecord as seen from the caller's session (self.db).
        """
        # 1) Try to create/commit the IN_PROGRESS row in an isolated session
        try:
            with SessionLocal() as s:
                rec = IdempotencyRecord(key=key, operation=operation, status=IdempotencyStatus.IN_PROGRESS)
                s.add(rec)
                s.commit()  # commit immediately so other sessions can see it
        except IntegrityError:
            # another request created it concurrently; ignore
            pass

        # 2) Return the row from the caller's session (self.db) so the caller works with objects it owns
        #    (this will now see the committed row either IN_PROGRESS or COMPLETED)
        return self.get(key)

    def mark_completed(self, key: str, response_body: dict):
        rec = self.get(key)
        if not rec:
            raise RuntimeError("Idempotency record missing")
        rec.status = IdempotencyStatus.COMPLETED
        rec.response_body = response_body
        self.db.flush()
        return rec

    def mark_failed(self, key: str, error_message: str):
        rec = self.get(key)
        if not rec:
            rec = IdempotencyRecord(key=key, operation="unknown", status=IdempotencyStatus.FAILED, last_error=error_message)
            self.db.add(rec)
            self.db.flush()
            return rec
        rec.status = IdempotencyStatus.FAILED
        rec.last_error = error_message
        self.db.flush()
        return rec