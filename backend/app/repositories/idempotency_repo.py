from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.idempotency import IdempotencyRecord, IdempotencyStatus
from app.db import SessionLocal  # new short-lived sessions for atomic begin

class IdempotencyRepository:
    def __init__(self, db: Session):
        # db is the caller's session (longer-lived)
        self.db = db

    def get(self, key: str):
        """
        Return the idempotency record for `key`. Expire session state first so
        we read fresh data from the DB and avoid stale objects in long-lived sessions.
        """
        try:
            try:
                self.db.expire_all()
            except Exception:
                pass
            rec = self.db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()
            if rec:
                try:
                    self.db.refresh(rec)
                except Exception:
                    pass
            return rec
        except Exception:
            return self.db.query(IdempotencyRecord).filter(IdempotencyRecord.key == key).first()

    def begin(self, key: str, operation: str) -> IdempotencyRecord:
            
        # 1. Check if record already exists and is not IN_PROGRESS (e.g., COMPLETED or FAILED)
        # Use get() for the freshest state from caller session
        existing_rec = self.get(key)
        if existing_rec:
            # If the record is already there, return it immediately. 
            # The caller (OrderService) will check its status (COMPLETED)
            return existing_rec 

        # 2. If it does not exist (or concurrent attempt), create IN_PROGRESS in a short-lived session (atomic insert)
        try:
            with SessionLocal() as s:
                rec = IdempotencyRecord(key=key, operation=operation, status=IdempotencyStatus.IN_PROGRESS)
                s.add(rec)
                s.commit()
        except IntegrityError:
            # Another request finished first, already exists -> fine. Continue to return the freshest record.
            pass

        # return the freshest record from caller session (this will read the COMPLETED record if the other process committed)
        rec = self.get(key)
        return rec

    def store(self, key: str, operation: str, response_body: dict, merge: bool = True):
        """
        Store partial response data into the idempotency record WITHOUT changing status.
        Useful for sub-operations (e.g. storing payment_result) while the overall operation
        remains IN_PROGRESS. If merge=True and the existing response_body is a dict, merge keys.
        """
        rec = self.get(key)
        if not rec:
            # create a new IN_PROGRESS record with the partial response
            rec = IdempotencyRecord(key=key, operation=operation, status=IdempotencyStatus.IN_PROGRESS, response_body=response_body)
            self.db.add(rec)
            self.db.flush()
            return rec

        # merge or replace existing response_body
        existing = rec.response_body or {}
        if merge and isinstance(existing, dict) and isinstance(response_body, dict):
            existing.update(response_body)
            rec.response_body = existing
        else:
            rec.response_body = response_body
        # keep status unchanged (do not mark COMPLETED here)
        self.db.flush()
        return rec

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
