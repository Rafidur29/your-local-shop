import uuid

class MockCourierAdapter:
    def is_available(self) -> bool:
        return True

    def book_shipment(self, order_id: int, address: dict):
        tracking = f"TRACK-{uuid.uuid4().hex[:10]}"
        return {"carrier":"MockCourier", "trackingNumber": tracking, "status":"booked"}
