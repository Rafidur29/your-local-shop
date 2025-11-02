from typing import Optional

from app.db import get_db
from app.services.cart_service import CartService
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/cart", tags=["cart"])


class AddItemIn(BaseModel):
    sku: str
    qty: int


def _get_cart_uuid_cookie(request: Request) -> Optional[str]:
    return request.cookies.get("cart_uuid")


@router.get("", summary="Get cart")
def get_cart(request: Request, db: Session = Depends(get_db)):
    cart_uuid = _get_cart_uuid_cookie(request)
    svc = CartService(db)
    cart = svc.get_or_create_cart_for_guest(cart_uuid)
    # Compute totals
    items = []
    total = 0
    for it in cart.items:
        items.append(
            {
                "id": it.id,
                "sku": it.sku,
                "quantity": it.quantity,
                "price_snapshot": it.price_snapshot,
            }
        )
        total += it.quantity * it.price_snapshot
    return {"cart_uuid": cart.cart_uuid, "items": items, "total_cents": total}


@router.post("/items", summary="Add item to cart")
def add_item(
    payload: AddItemIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    cart_uuid = _get_cart_uuid_cookie(request)
    svc = CartService(db)
    cart = svc.get_or_create_cart_for_guest(cart_uuid)
    try:
        item = svc.add_item(cart, payload.sku, payload.qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # set cookie if was created
    response.set_cookie("cart_uuid", cart.cart_uuid, httponly=False, samesite="Lax")
    return {"item_id": item.id, "cart_uuid": cart.cart_uuid}


@router.delete("/items/{item_id}", summary="Remove item")
def remove_item(item_id: int, request: Request, db: Session = Depends(get_db)):
    cart_uuid = _get_cart_uuid_cookie(request)
    svc = CartService(db)
    cart = svc.get_or_create_cart_for_guest(cart_uuid)
    svc.remove_item(cart, item_id)
    return {"ok": True}
