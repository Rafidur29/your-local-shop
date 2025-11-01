import time
import random
from uuid import uuid4
from typing import Dict, Optional

from app.repositories.idempotency_repo import IdempotencyRepository

class PaymentDeclined(Exception):
    """Raised for a non-retryable payment failure (e.g., insufficient funds)."""
    pass

class PaymentTransientError(Exception):
    """Raised for a temporary gateway error, suggesting a retry is appropriate."""
    pass

class MockPaymentAdapter:
    """
    Simple mock payment adapter using a database repository for durable idempotency.
    """

    def __init__(self, idempotency_repo, delay_ms: int = 200):
        # The idempotency_repo is injected, likely initialized with a DB session via DI
        self.idempotency_repo = idempotency_repo
        # Convert delay from milliseconds to seconds for time.sleep
        self.delay_seconds = delay_ms / 1000.0

    def charge(self, db_session, amount_cents: int, payment_method: Dict, idempotency_key: Optional[str] = None):
        """
        Simulates a payment charge. Supports database-backed idempotency check/storage.

        Args:
            db_session: The active SQLAlchemy session for persistence.
            amount_cents: The amount to charge.
            payment_method: Dictionary containing payment details (can include "force_decline").
            idempotency_key: Optional key to ensure the charge runs only once.
        
        Returns:
            A dictionary representing the successful transaction.
        
        Raises:
            PaymentDeclined: If a deterministic failure is simulated.
            PaymentTransientError: If a random, temporary gateway error is simulated.
        """
        # If the idempotency record already contains a saved payment_result, return it.
        if idempotency_key:
            rec = None
            try:
                rec = self.idempotency_repo.get(idempotency_key)
            except Exception:
                # repository might not be available / configured - fall back to simulated behavior
                rec = None

            if rec and getattr(rec, "response_body", None):
                # response_body may contain partial results like {"payment_result": {...}}
                pr = rec.response_body.get("payment_result") if isinstance(rec.response_body, dict) else None
                if pr:
                    return pr

        # Simulate network latency / gateway processing
        time.sleep(self.delay_seconds)

        # Simulate deterministic decline if requested by the test payload
        if payment_method and isinstance(payment_method, dict) and payment_method.get("force_decline"):
            raise PaymentDeclined("Simulated forced decline")

        # Simulate a random transient failure (low probability)
        if random.random() < 0.01:
            raise PaymentTransientError("Simulated transient gateway error")

        # --- 2. Simulate Success ---
        txn = {
            "transaction_id": f"mock-{uuid4().hex}", 
            "status": "captured", 
            "amount_cents": amount_cents
        }
        
        # --- 3. Store Idempotency partial result (payment_result) WITHOUT marking overall operation completed ---
        if idempotency_key:
            try:
                # store partial result into the idempotency record (merge with any existing response_body)
                self.idempotency_repo.store(
                    key=idempotency_key, 
                    operation="charge", 
                    response_body={"payment_result": txn}
                )
                # ensure the caller's session sees the stored data
                db_session.flush()
            except Exception:
                # best-effort: if store fails, just continue — payment succeeded (tests are single-threaded)
                pass
            
        return txn

    def refund(self, transaction_id: str) -> Dict:
        """Simulates a refund."""
        time.sleep(self.delay_seconds)
        return {
            "refund_id": f"refund-{uuid4().hex}", 
            "status": "refunded", 
            "transaction_id": transaction_id
        }
