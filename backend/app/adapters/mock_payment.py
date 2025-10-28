import time
import uuid
from app.config import settings

class MockPaymentAdapter:
    def __init__(self, delay_ms: int = None):
        self.delay_ms = delay_ms if delay_ms is not None else settings.PAYMENT_MOCK_DELAY_MS
        self._idempotency = {}

    def is_available(self) -> bool:
        return True

    def charge(self, token_or_card: str, amount_cents: int, idempotency_key: str):
        if idempotency_key and idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]

        time.sleep(self.delay_ms / 1000.0)
        tx = {
            "transactionId": f"mockpay_{uuid.uuid4().hex}",
            "status": "captured",
            "amount_cents": amount_cents
        }
        if idempotency_key:
            self._idempotency[idempotency_key] = tx
        return tx

    def refund(self, transaction_id: str):
        return {"refundId": f"refund_{uuid.uuid4().hex}", "transactionId": transaction_id, "status": "refunded"}

    def tokenize(self, card_number: str, expiry: str, name: str):
        token = f"token_{uuid.uuid4().hex}"
        return {"tokenId": token, "last4": card_number[-4:]}
