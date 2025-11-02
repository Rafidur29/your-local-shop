from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.adapters.mock_payment import MockPaymentAdapter, PaymentTransientError
from app.models.credit_note import CreditNote
from app.models.idempotency import IdempotencyStatus
from app.models.order import Invoice, Order, OrderLine
from app.models.product import Product
from app.models.return_line import ReturnLine
from app.models.return_request import ReturnRequest
from app.repositories.idempotency_repo import IdempotencyRepository
from app.services.inventory_service import InventoryService
from app.utils.transactions import smart_transaction
from sqlalchemy.orm import Session


class ReturnServiceException(Exception):
    pass


class ReturnService:
    def __init__(self, db: Session):
        self.db = db
        self.idem_repo = IdempotencyRepository(db)
        self.payment_adapter = MockPaymentAdapter(self.idem_repo, delay_ms=0)
        self.inventory = InventoryService(db)

    def _gen_rma(self):
        return f"RMA-{uuid4().hex[:10].upper()}"

    def create_return(
        self, order_id: int, lines: list, created_by: Optional[str] = None
    ):
        """Create a return request (RMA) for a COMPLETED order"""
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ReturnServiceException("Order not found")
        if getattr(order, "status", "").upper() != "COMPLETED":
            raise ReturnServiceException("Can only create return for completed orders")

        # map order lines by sku for validation
        # Use an explicit query to ensure we get actual persisted order lines regardless of relationship state
        order_lines = (
            self.db.query(OrderLine).filter(OrderLine.order_id == order_id).all()
        )
        order_line_map = {ol.sku: ol for ol in order_lines}

        for li in lines:
            sku = li.get("sku")
            qty = int(li.get("qty", 1))
            if sku not in order_line_map:
                raise ReturnServiceException(f"SKU {sku} not part of order")
            ol = order_line_map[sku]
            if qty > getattr(ol, "qty", 0):
                raise ReturnServiceException(
                    f"Cannot return more than purchased for {sku}"
                )

        rr = ReturnRequest(
            rma_number=self._gen_rma(),
            order_id=order_id,
            status="REQUESTED",
            data={"created_by": created_by},
        )
        self.db.add(rr)
        self.db.flush()

        for li in lines:
            ol = order_line_map[li["sku"]]
            rl = ReturnLine(
                return_id=rr.id,
                order_line_id=ol.id,
                sku=li["sku"],
                qty=int(li.get("qty", 1)),
                reason=li.get("reason"),
            )
            # set unit_amount_cents on the return line if attribute exists
            if hasattr(rl, "unit_amount_cents"):
                price = (
                    getattr(ol, "unit_price_cents", None)
                    or getattr(ol, "unit_price", None)
                    or getattr(ol, "price_cents", None)
                )
                rl.unit_amount_cents = price
            self.db.add(rl)

        self.db.commit()
        self.db.refresh(rr)
        return rr

    def get_return(self, rma_id: int):
        return self.db.query(ReturnRequest).filter(ReturnRequest.id == rma_id).first()

    def receive_return(self, rma_id: int, idempotency_key: Optional[str] = None):
        """
        Mark the return as received, attempt refund (if payment transaction is available),
        create a CreditNote and restock inventory. Operation is idempotent if idempotency_key provided.
        """
        idem_key = None
        if idempotency_key:
            idem_key = f"return.receive:{rma_id}:{idempotency_key}"
            try:
                rec, created = self.idem_repo.begin(
                    idem_key, operation="return_receive"
                )
            except Exception:
                rec, created = (None, False)

            # robust completed check (same helper)
            def _is_completed(rr):
                if not rr:
                    return False
                try:
                    if rr.status == IdempotencyStatus.COMPLETED:
                        return True
                except Exception:
                    pass
                if getattr(rr.status, "name", None) == "COMPLETED":
                    return True
                if str(rr.status).upper() == "COMPLETED":
                    return True
                return False

            # if not created, wait briefly for owner to finish
            if not created:
                if rec and _is_completed(rec) and getattr(rec, "response_body", None):
                    return rec.response_body

                import time

                timeout = 2.0
                start = time.time()
                while time.time() - start < timeout:
                    rec = self.idem_repo.get(idem_key)
                    if _is_completed(rec) and getattr(rec, "response_body", None):
                        return rec.response_body
                    time.sleep(0.05)

        rr = self.get_return(rma_id)
        if not rr:
            raise ReturnServiceException("RMA not found")

        # REMOVE or comment out the partial return:
        # if rr.status == "REFUNDED":
        #    return {"credit_note_id": rr.credit_note.id if rr.credit_note else None}

        if rr.status == "REFUNDED":
            # The operation is finished, but we need to retrieve the full response to pass the test.
            # Find the full details from the existing CreditNote
            if rr.credit_note:
                credit = rr.credit_note
                refund_resp = (
                    credit.data.get("refund")
                    if credit.data and isinstance(credit.data, dict)
                    else None
                )
                return {
                    "credit_note_id": credit.id,
                    "credit_no": credit.credit_no,
                    "amount_cents": credit.amount_cents,
                    "refund": refund_resp,
                }
            # Fallback to the partial response if CreditNote is somehow missing but status is REFUNDED
            return {"credit_note_id": rr.credit_note.id if rr.credit_note else None}

        # compute refund total robustly
        total = 0
        for rl in rr.lines:
            if getattr(rl, "unit_amount_cents", None) is not None:
                total += (rl.unit_amount_cents or 0) * rl.qty
            else:
                ol = (
                    self.db.query(OrderLine)
                    .filter(OrderLine.id == rl.order_line_id)
                    .first()
                )
                if ol:
                    price = (
                        getattr(ol, "unit_price_cents", None)
                        or getattr(ol, "unit_price", None)
                        or getattr(ol, "price_cents", 0)
                    )
                    total += (price or 0) * rl.qty

        # persist RECEIVED_PENDING_REFUND status
        rr.status = "RECEIVED_PENDING_REFUND"
        self.db.add(rr)
        self.db.commit()

        # find invoice transaction id if available
        invoice = self.db.query(Invoice).filter(Invoice.order_id == rr.order_id).first()
        transaction_id = None
        if invoice and invoice.data and isinstance(invoice.data, dict):
            transaction_id = invoice.data.get("payment", {}).get(
                "transaction_id"
            ) or invoice.data.get("transaction_id")

        refund_resp = None
        credit = None
        try:
            if transaction_id:
                refund_resp = self.payment_adapter.refund(transaction_id)

            with smart_transaction(self.db):
                credit = CreditNote(
                    credit_no=f"CN-{uuid4().hex[:8].upper()}",
                    order_id=rr.order_id,
                    return_id=rr.id,
                    amount_cents=total,
                    tax_cents=0,
                    data={"refund": refund_resp},
                )
                self.db.add(credit)
                # restock product(s)
                for rl in rr.lines:
                    prod = self.db.query(Product).filter(Product.sku == rl.sku).first()
                    if prod:
                        prod.stock = (prod.stock or 0) + rl.qty
                        self.db.add(prod)
                rr.status = "REFUNDED"
                self.db.add(rr)

        except PaymentTransientError as e:
            # keep pending and mark idem failed (so caller/retry can handle)
            rr.status = "RECEIVED_PENDING_REFUND"
            self.db.add(rr)
            self.db.commit()
            if idem_key:
                self.idem_repo.mark_failed(idem_key, str(e))
            raise ReturnServiceException(f"Transient payment error: {e}")

        except Exception as e:
            rr.status = "FAILED"
            self.db.add(rr)
            self.db.commit()
            if idem_key:
                self.idem_repo.mark_failed(idem_key, str(e))
            raise ReturnServiceException(f"Failed to process return: {e}")

        resp = {
            "credit_note_id": credit.id,
            "credit_no": credit.credit_no,
            "amount_cents": credit.amount_cents,
            "refund": refund_resp,
        }
        if idem_key:
            self.idem_repo.mark_completed(idem_key, resp)
        return resp
