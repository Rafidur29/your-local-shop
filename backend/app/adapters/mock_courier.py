import time
from uuid import uuid4
from typing import Dict

class CourierError(Exception):
    pass

class MockCourierAdapter:
    """
    Simple synchronous mock courier adapter.
    book_shipment returns a dict {courier, tracking_number, status}
    """
    def __init__(self, delay_ms: int = 100):
        self.delay = delay_ms / 1000.0

    def book_shipment(self, order_id: int, pickup_address: Dict = None, parcels: Dict = None) -> Dict:
        # simulate latency
        time.sleep(self.delay)
        # deterministic tracking number for testing (uuid)
        tracking = f"TRK-{uuid4().hex[:12].upper()}"
        return {"courier": "mock-courier", "tracking_number": tracking, "status": "booked"}
