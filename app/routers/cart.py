from fastapi import APIRouter, Depends, Cookie, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..db import get_db
from ..models import Cart, CartItem, ProductVariant
from ..services.inventory import InventoryService  # assuming you have this
from ..schemas import CartItemIn

router = APIRouter(prefix="/api/cart", tags=["Cart"])


def _find_or_create_cart(db: Session, cartid: Optional[int] = None):
    cart = db.query(Cart).filter_by(id=cartid).first() if cartid else None
    if not cart:
        cart = Cart()
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


@router.post("/items")
def add_item(
    payload: CartItemIn,
    db: Session = Depends(get_db),
    cartid: Optional[int] = Cookie(None),
):
    cart = _find_or_create_cart(db, cartid)

    # get price snapshot from product variant (or product)
    pv = db.query(ProductVariant).filter_by(sku=payload.sku).first()
    if not pv:
        raise HTTPException(404, "SKU not found")

    inv = InventoryService(db)
    if payload.qty > inv.available_stock(payload.sku):
        raise HTTPException(409, "Not enough stock")

    # upsert unique (cart, sku)
    item = db.query(CartItem).filter_by(cart_id=cart.id, sku=payload.sku).first()
    if item:
        item.qty += payload.qty
    else:
        item = CartItem(
            cart_id=cart.id,
            sku=payload.sku,
            qty=payload.qty,
            price_snapshot=pv.price_cents,
        )
        db.add(item)

    db.commit()
    return {"id": item.id}


@router.patch("/items/{item_id}")
def update_item(item_id: int, payload: CartItemIn, db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")

    inv = InventoryService(db)
    if payload.qty <= 0:
        db.delete(item)
    else:
        if payload.qty > inv.available_stock(item.sku) + item.qty:
            raise HTTPException(409, "Not enough stock for requested quantity")
        item.qty = payload.qty

    db.commit()
    return {"ok": True}


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id).first()
    if not item:
        return
    db.delete(item)
    db.commit()


@router.post("/merge")
def merge_cart(
    guest_cart_id: int,
    user_cart_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    guest = db.query(Cart).filter_by(id=guest_cart_id).first()
    if not guest:
        raise HTTPException(404, "Guest cart not found")

    target = _find_or_create_cart(db, user_cart_id)

    for gi in guest.items:
        ti = db.query(CartItem).filter_by(cart_id=target.id, sku=gi.sku).first()
        if ti:
            ti.qty += gi.qty
        else:
            db.add(
                CartItem(
                    cart_id=target.id,
                    sku=gi.sku,
                    qty=gi.qty,
                    price_snapshot=gi.price_snapshot,
                )
            )

    db.delete(guest)
    db.commit()
    return {"cartId": target.id}
