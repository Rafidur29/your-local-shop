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
        if idempotency_key:
            rec = self.idempotency_repo.get(idempotency_key)
            if rec:
                # Return the stored result for a repeated call with the same key
                return rec.response_body.get("payment_result")
        
        # Simulate delay
        time.sleep(self.delay_seconds)
        
        # --- 1. Simulate Errors ---
        if payment_method.get("force_decline"):
            raise PaymentDeclined("Mock decline: Payment method indicated a forced decline.")
        
        # Simulate transient error randomly (1% chance)
        if random.random() < 0.01:
            raise PaymentTransientError("Transient gateway error: Please retry the payment.")

        # --- 2. Simulate Success ---
        txn = {
            "transaction_id": f"mock-{uuid4().hex}", 
            "status": "captured", 
            "amount_cents": amount_cents
        }
        
        # --- 3. Store Idempotency Record ---
        if idempotency_key:
            # Store the transaction result in the database via the repository
            # Operation is explicitly defined as "charge"
            self.idempotency_repo.store(
                key=idempotency_key, 
                operation="charge", 
                response_body={"payment_result": txn}
            )
            # Flush to make the record visible in the current transaction 
            # (caller manages the final commit).
            db_session.flush() 
            
        return txn

    def refund(self, transaction_id: str) -> Dict:
        """Simulates a refund."""
        time.sleep(self.delay_seconds)
        return {
            "refund_id": f"refund-{uuid4().hex}", 
            "status": "refunded", 
            "transaction_id": transaction_id
        }