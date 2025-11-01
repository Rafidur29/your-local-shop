from typing import List, Dict, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.order import Order, OrderLine, Invoice
from app.repositories.idempotency_repo import IdempotencyRepository
from app.services.inventory_service import InventoryService, InventoryException
from app.adapters.mock_payment import MockPaymentAdapter, PaymentDeclined, PaymentTransientError
from app.models.product import Product
from app.utils.transactions import smart_transaction
from app.models.idempotency import IdempotencyStatus, IdempotencyRecord 
from app.services.fulfilment_service import FulfilmentService


class OrderServiceException(Exception):
    pass

class OrderService:
    def __init__(self, db: Session):
        self.db = db
        self.idem_repo = IdempotencyRepository(db)
        self.inventory = InventoryService(db)
        self.payment_adapter = MockPaymentAdapter(self.idem_repo, delay_ms=200)

    def _gen_order_number(self) -> str:
        return f"ORD-{uuid4().hex[:10].upper()}"

    def create_order(self, customer_id: Optional[int], items: List[Dict], payment_method: Dict, idempotency_key: Optional[str] = None) -> Dict:
        """
        items: list of {sku: str, qty: int}
        payment_method: dict (mock)
        idempotency_key: string key for idempotency
        Returns a dict response to be returned by API.
        """
        # check idempotency first
        if idempotency_key:
            try:
                # Use smart_transaction to ensure the IN_PROGRESS record is COMMITTED immediately
                with smart_transaction(self.db):
                    rec = self.idem_repo.begin(idempotency_key, "create_order")
                    
                    if rec.status == IdempotencyStatus.COMPLETED:
                        return rec.response_body # Return cached response immediately
                    
                    # If the record is IN_PROGRESS (meaning another request created the lock), 
                    # we must BLOCK this request. This handles both tight races and previous partial runs.
                    if rec.status == IdempotencyStatus.IN_PROGRESS:
                        # Since we rely on the repository to handle FAILED records by resetting them to IN_PROGRESS
                        # and updating 'updated_at', checking for IN_PROGRESS is the safest block.
                        raise OrderServiceException("Duplicate request in progress or prior request is incomplete, try again later")
                    
                    # If the status is FAILED (implying the record was reset by the repository's begin method) 
                    # or NEWLY created, we proceed.
                    
            except OrderServiceException:
                # Re-raise the explicit block exception
                raise
            except Exception as e:
                # Handle general database/repository errors during the check
                raise OrderServiceException(f"Idempotency begin failed: {str(e)}")

        # 1) Validate products & compute total
        lines = []
        total_cents = 0
        
        # NOTE: Moved import to file top. It was here: from app.models.product import Product
        
        for it in items:
            sku = it["sku"]
            qty = int(it["qty"])
            p = self.db.query(Product).filter(Product.sku == sku, Product.active == True).first()
            if not p:
                raise OrderServiceException(f"SKU {sku} not found")
            lines.append({"sku": sku, "name": p.name, "qty": qty, "price_cents": p.price_cents})
            total_cents += p.price_cents * qty

        # 2) Reserve inventory for each line (collect reservation ids)
        reservations = []
        try:
            for l in lines:
                r = self.inventory.reserve(l["sku"], l["qty"])
                reservations.append(r)
        except InventoryException as e:
            # release any created reservations
            for r in reservations:
                try:
                    self.inventory.release(r.id)
                except Exception:
                    pass
            raise OrderServiceException(f"Inventory reservation failed: {str(e)}")

        # 3) Call payment adapter (idempotent)
        try:
            # possible transient retry logic
            max_retries = 2
            attempt = 0
            payment_tx = None
            while True:
                try:
                    payment_tx = self.payment_adapter.charge(self.db, total_cents, payment_method, idempotency_key=idempotency_key)
                    break # Successful charge
                except PaymentTransientError:
                    attempt += 1
                    if attempt > max_retries:
                        raise # Re-raise if retries exceeded
                    # small backoff
                    import time; time.sleep(0.2 * (2 ** attempt))
            
            # This is the correct position for the two exceptions below, OUTSIDE the while loop:
        except PaymentDeclined as e:
            # release all reservations
            for r in reservations:
                try:
                    self.inventory.release(r.id)
                except Exception:
                    pass # Ignore if release fails
            
            # Mark idempotency FAILED upon final decline AFTER releasing reservations
            if idempotency_key:
                with smart_transaction(self.db):
                    self.idem_repo.mark_failed(idempotency_key, f"Payment declined: {str(e)}")
            
            raise OrderServiceException(f"Payment declined: {str(e)}") # <-- Raise OrderServiceException here
        except OrderServiceException:
            # Re-raise explicit OrderServiceException
            raise
        except Exception as e:
            # unknown payment error -> release and bubble
            for r in reservations:
                try:
                    self.inventory.release(r.id)
                except Exception:
                    pass
            if idempotency_key:
                with smart_transaction(self.db):
                    self.idem_repo.mark_failed(idempotency_key, f"Payment failed with unknown error: {str(e)}")
            raise OrderServiceException(f"Payment failed: {str(e)}") # <-- Raise OrderServiceException here


        # 4) Payment succeeded -> create order + invoice + commit reservations
        # We perform DB work within a transaction
        with smart_transaction(self.db):
            order = Order(
                order_number=self._gen_order_number(),
                customer_id=customer_id,
                status="COMPLETED",
                total_cents=total_cents, # NOTE: Removed the accidental multiplication by 47
                created_at=datetime.now(timezone.utc), # NOTE: Changed datetime to datetime.now(timezone.utc) for consistency
                data={"payment_tx": payment_tx}, # NOTE: Changed metadata to data to match model definition
            )
            self.db.add(order)
            self.db.flush()  # get order.id
            for l in lines:
                ol = OrderLine(order_id=order.id, sku=l["sku"], name=l["name"], qty=l["qty"], price_cents=l["price_cents"])
                self.db.add(ol)

            # create invoice
            invoice = Invoice(order_id=order.id, invoice_no=f"INV-{uuid4().hex[:8].upper()}", total_cents=total_cents, tax_cents=0)
            self.db.add(invoice)
            self.db.flush()
            # At this point order and invoice exist and have IDs
            
            try:
                fulfil = FulfilmentService(self.db)
                fulfil.create_packing_task_for_order(order.id)
            except Exception:
                # non-fatal; just log -- do not break order creation
                pass

        # 5) commit reservations (decrement stock)
        committed_ids = []
        try:
            for r in reservations:
                committed = self.inventory.commit(r.id, order_id=order.id)
                committed_ids.append(committed.id)
        except Exception as commit_exc:
            # If commit fails after payment, attempt refund and mark order as REFUNDED/FAILED
            try:
                # attempt refund
                self.payment_adapter.refund(payment_tx["transaction_id"])
            except Exception:
                pass
            
            if idempotency_key:
                with smart_transaction(self.db):
                    self.idem_repo.mark_failed(idempotency_key, f"Inventory commit failed: {str(commit_exc)}")
            # mark order failed/refunded in DB
            with self.db.begin():
                order.status = "REFUNDED"
                self.db.add(order)
            raise OrderServiceException(f"Inventory commit failed after payment: {str(commit_exc)}")

        # 6) store idempotency response if key provided
        resp = {
            "orderId": order.id,
            "orderNumber": order.order_number,
            "status": order.status,
            "invoiceId": invoice.id,
            "payment": payment_tx,
        }
        if idempotency_key:
            with smart_transaction(self.db):
            # store the response object for idempotency
                self.idem_repo.mark_completed(idempotency_key, resp) 
        return resp