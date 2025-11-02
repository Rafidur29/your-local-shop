from typing import Dict, Optional

from app.adapters.mock_courier import CourierError, MockCourierAdapter
from app.models.packing_task import PackingTask
from app.models.shipment import Shipment
from app.utils.transactions import smart_transaction
from sqlalchemy.orm import Session


class FulfilmentException(Exception):
    pass


class FulfilmentService:
    def __init__(
        self, db: Session, courier_adapter: Optional[MockCourierAdapter] = None
    ):
        self.db = db
        self.courier = courier_adapter or MockCourierAdapter(delay_ms=150)

    def create_packing_task_for_order(
        self,
        order_id: int,
        assigned_to: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> PackingTask:
        with smart_transaction(self.db):
            task = PackingTask(
                order_id=order_id,
                status="pending",
                assigned_to=assigned_to,
                details=metadata,
            )
            self.db.add(task)
            self.db.flush()
            return task

    def list_pending_tasks(self, limit: int = 100):
        return (
            self.db.query(PackingTask)
            .filter(PackingTask.status == "pending")
            .order_by(PackingTask.created_at)
            .limit(limit)
            .all()
        )

    def mark_packed_and_book(
        self,
        packing_task_id: int,
        pickup_address: Optional[Dict] = None,
        parcels: Optional[Dict] = None,
    ) -> Shipment:
        """
        Mark packing task as packed, attempt to book shipment with courier, create Shipment row and return it.
        All done transactionally where possible.
        """
        # We'll create shipment inside a smart_transaction. We want to persist the change to PackingTask even if courier fails?
        # Prefer: if courier booking fails, mark task status='error' and raise FulfilmentException.
        with smart_transaction(self.db):
            task = (
                self.db.query(PackingTask)
                .filter(PackingTask.id == packing_task_id)
                .with_for_update()
                .first()
            )
            if not task:
                raise FulfilmentException("PackingTask not found")
            if task.status != "pending":
                raise FulfilmentException(
                    f"PackingTask not in pending state (current={task.status})"
                )
            # attempt booking
            try:
                booking = self.courier.book_shipment(
                    order_id=task.order_id,
                    pickup_address=pickup_address,
                    parcels=parcels,
                )
            except Exception as e:
                task.status = "error"
                self.db.flush()
                raise FulfilmentException(f"Courier booking failed: {str(e)}")
            # create shipment row
            shipment = Shipment(
                packing_task_id=task.id,
                order_id=task.order_id,
                courier=booking.get("courier", "mock-courier"),
                tracking_number=booking["tracking_number"],
                status=booking.get("status", "booked"),
                data=booking,
            )
            self.db.add(shipment)
            # mark task packed
            task.status = "packed"
            self.db.flush()
            # refresh to ensure IDs populated
            self.db.refresh(shipment)
            return shipment
