import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import SessionLocal  # new short-lived sessions for atomic begin
from app.models.idempotency import IdempotencyRecord, IdempotencyStatus

log = logging.getLogger("idempotency")
log.setLevel(logging.DEBUG)
if not log.handlers:
    import sys

    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("[IDEMPOTENCY] %(message)s"))
    log.addHandler(h)


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
            rec = (
                self.db.query(IdempotencyRecord)
                .filter(IdempotencyRecord.key == key)
                .first()
            )
            if rec:
                try:
                    self.db.refresh(rec)
                except Exception:
                    pass
            return rec
        except Exception:
            return (
                self.db.query(IdempotencyRecord)
                .filter(IdempotencyRecord.key == key)
                .first()
            )

    def begin(self, key: str, operation: str) -> tuple:
        """
        Atomically ensure an idempotency row exists.
        Returns (IdempotencyRecord_from_caller_session, created_flag)
          - created_flag == True  -> this call successfully created the IN_PROGRESS row (owner)
          - created_flag == False -> row already existed (concurrent / previous request)

        Uses a short-lived SessionLocal() to INSERT+COMMIT so visibility is immediate.
        """
        created = False
        log.debug(f"begin(): trying insert key={key!r}")
        try:
            with SessionLocal() as s:
                rec = IdempotencyRecord(
                    key=key, operation=operation, status=IdempotencyStatus.IN_PROGRESS
                )
                s.add(rec)
                s.commit()
                created = True
        except IntegrityError:
            log.debug(f"begin(): insert collision for key={key!r}")
            created = False

        # return the record as seen by the caller's session + the created flag
        log.debug(
            f"begin(): returning rec.key={self.get(key).key if self.get(key) else None} created={created}"
        )
        return self.get(key), created

    def store(self, key: str, operation: str, response_body: dict, merge: bool = True):
        """
        Store partial response data into the idempotency record WITHOUT changing status.
        Useful for sub-operations (e.g. storing payment_result) while the overall operation
        remains IN_PROGRESS. If merge=True and the existing response_body is a dict, merge keys.
        """
        rec = self.get(key)
        if not rec:
            # create a new IN_PROGRESS record with the partial response
            rec = IdempotencyRecord(
                key=key,
                operation=operation,
                status=IdempotencyStatus.IN_PROGRESS,
                response_body=response_body,
            )
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
        """
        Mark an idempotency record as COMPLETED and persist response_body.
        Use a short-lived session to ensure the update is committed/visible to other sessions immediately.
        """
        # Use a short-lived session to ensure the completed state is committed and visible immediately.
        try:
            with SessionLocal() as s:
                rec = (
                    s.query(IdempotencyRecord)
                    .filter(IdempotencyRecord.key == key)
                    .first()
                )
                if not rec:
                    raise RuntimeError(
                        "Idempotency record missing for key: " + str(key)
                    )
                rec.status = IdempotencyStatus.COMPLETED
                rec.response_body = response_body
                s.add(rec)
                s.commit()
                log.debug(
                    f"mark_completed(): key={key!r} response_keys={list(response_body.keys()) if isinstance(response_body, dict) else type(response_body)}"
                )
        except Exception:
            # fallback to caller session update (best-effort)
            rec = self.get(key)
            if not rec:
                raise RuntimeError("Idempotency record missing")
            rec.status = IdempotencyStatus.COMPLETED
            rec.response_body = response_body
            self.db.flush()
        return self.get(key)

    def mark_failed(self, key: str, error_message: str):
        rec = self.get(key)
        if not rec:
            rec = IdempotencyRecord(
                key=key,
                operation="unknown",
                status=IdempotencyStatus.FAILED,
                last_error=error_message,
            )
            self.db.add(rec)
            self.db.flush()
            return rec
        rec.status = IdempotencyStatus.FAILED
        rec.last_error = error_message
        self.db.flush()
        return rec
