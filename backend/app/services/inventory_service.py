import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.config import settings
from app.models.inventory_reservation import InventoryReservation
from app.models.product import Product
from app.utils.transactions import smart_transaction
from filelock import FileLock, Timeout
from sqlalchemy import func
from sqlalchemy.orm import Session


class InventoryException(Exception):
    pass


class InventoryService:
    def __init__(self, db: Session):
        self.db = db

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def available_quantity(self, sku: str) -> int:
        """
        Determine available quantity = product.stock - sum(active reservations)
        """
        qry = self.db.query(Product).filter(Product.sku == sku)

        # Only add active filter if the Product model actually has that attribute
        if hasattr(Product, "active"):
            qry = qry.filter(Product.active == True)

        # Acquire row-level lock when available (SQLAlchemy with_for_update)
        try:
            product = qry.with_for_update().first()
        except Exception:
            # Some DB dialects/environments don't support with_for_update; fall back to plain first()
            product = qry.first()

        if not product:
            raise InventoryException("SKU not found")
        now = self._now()
        reserved_sum = (
            self.db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0))
            .filter(
                InventoryReservation.sku == sku,
                InventoryReservation.status == "reserved",
                InventoryReservation.reserved_until > now,
            )
            .scalar()
            or 0
        )
        return max(0, product.stock - int(reserved_sum))

    def reserve(
        self, sku: str, qty: int, ttl_seconds: Optional[int] = None
    ) -> InventoryReservation:
        if qty <= 0:
            raise InventoryException("Quantity must be positive")
        ttl_seconds = ttl_seconds or settings.RESERVATION_TTL_SECONDS
        now = self._now()
        reserved_until = now + timedelta(seconds=ttl_seconds)

        tempdir = tempfile.gettempdir()
        locks_dir = os.path.join(tempdir, "yourlocalshop_locks")
        os.makedirs(locks_dir, exist_ok=True)
        lockfile = os.path.join(locks_dir, f"reserve_{sku}.lock")

        lock = FileLock(lockfile)
        try:
            with lock.acquire(timeout=10):
                # Use smart_transaction to handle nested tx correctly
                with smart_transaction(self.db):
                    qry = self.db.query(Product).filter(Product.sku == sku)
                    if hasattr(Product, "active"):
                        qry = qry.filter(Product.active == True)
                    try:
                        product = qry.with_for_update().first()
                    except Exception:
                        # some DB backends or in-memory contexts may not support with_for_update; fall back to plain query
                        product = qry.first()

                    if not product:
                        raise InventoryException("SKU not found")

                    reserved_sum = (
                        self.db.query(
                            func.coalesce(func.sum(InventoryReservation.quantity), 0)
                        )
                        .filter(
                            InventoryReservation.sku == sku,
                            InventoryReservation.status == "reserved",
                            InventoryReservation.reserved_until > now,
                        )
                        .scalar()
                        or 0
                    )

                    available = product.stock - int(reserved_sum)
                    if available < qty:
                        raise InventoryException(
                            f"Not enough stock. Available={available}"
                        )

                    r = InventoryReservation(
                        sku=sku,
                        quantity=qty,
                        reserved_at=now,
                        reserved_until=reserved_until,
                        status="reserved",
                    )
                    self.db.add(r)
                    self.db.flush()  # ensure id assigned
                    # commit happens at smart_transaction context exit
                # after commit the row is durable — refresh the instance from the DB session
                self.db.refresh(r)
                return r
        except Timeout:
            raise InventoryException("Could not acquire reservation lock; try again")

    def release(self, reservation_id: int) -> InventoryReservation:
        r = (
            self.db.query(InventoryReservation)
            .filter(InventoryReservation.id == reservation_id)
            .with_for_update()
            .first()
        )
        if not r:
            raise InventoryException("Reservation not found")
        if r.status != "reserved":
            return r
        r.status = "released"
        self.db.flush()
        return r

    def commit(
        self, reservation_id: int, order_id: Optional[int] = None
    ) -> InventoryReservation:
        """
        Commit a reservation: decrement product.stock and mark reservation committed.
        """
        # Load the reservation and lock it
        r = (
            self.db.query(InventoryReservation)
            .filter(InventoryReservation.id == reservation_id)
            .with_for_update()
            .first()
        )
        if not r:
            raise InventoryException("Reservation not found")
        if r.status != "reserved":
            raise InventoryException("Reservation not active")

        # Use the SKU from the reservation (was a NameError previously because `sku` didn't exist)
        product = (
            self.db.query(Product)
            .filter(Product.sku == r.sku)
            .with_for_update()
            .first()
        )
        if not product:
            raise InventoryException("SKU not found")

        now = self._now()
        reserved_sum = (
            self.db.query(func.coalesce(func.sum(InventoryReservation.quantity), 0))
            .filter(
                InventoryReservation.sku == r.sku,
                InventoryReservation.status == "reserved",
                InventoryReservation.reserved_until > now,
            )
            .scalar()
            or 0
        )

        # available after excluding this reservation
        available = product.stock - (int(reserved_sum) - r.quantity)
        if available < r.quantity:
            raise InventoryException("Not enough stock to commit (race)")

        product.stock = product.stock - r.quantity
        r.status = "committed"
        r.order_id = order_id
        self.db.flush()
        return r

    def expire_overdue(self) -> List[int]:
        """
        Find reservations whose reserved_until < now and are still 'reserved', mark them 'expired'.
        Return list of expired reservation ids.
        """
        # Use smart_transaction to be robust if a caller has already started a transaction
        with smart_transaction(self.db):
            now = self._now()
            expired = (
                self.db.query(InventoryReservation)
                .filter(
                    InventoryReservation.status == "reserved",
                    InventoryReservation.reserved_until <= now,
                )
                .all()
            )
            ids = []
            for r in expired:
                r.status = "expired"
                ids.append(r.id)
            self.db.flush()
            return ids
