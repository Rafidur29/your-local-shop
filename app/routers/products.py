from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ..db import get_db
from ..models import Product, ProductVariant
from ..schemas import PaginatedProducts, ProductDetail, ProductListItem


router = APIRouter(prefix="/api/products", tags=["Catalogue"])


@router.get("", response_model=PaginatedProducts)
def list_products(
    q: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
):
    query = db.query(Product).filter(Product.active == True)
    if q:
        like = f"%{q}%"
        query = query.filter(Product.name.ilike(like))
    if category:
        query = query.filter(Product.category == category)
    total = query.count()
    items = (
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # create stockHint from first variant (demo)
    out_items = []
    for p in items:
        first_variant = db.query(ProductVariant).filter_by(product_id=p.id).first()
        stock_hint = first_variant.stock if first_variant else 0
        out_items.append(
            ProductListItem(
                sku=p.sku,
                name=p.name,
                price=p.price_cents,
                stockHint=stock_hint,
            )
        )
    return {"items": out_items, "page": page, "size": size, "total": total}


@router.get("/{sku}", response_model=ProductDetail)
def get_product(sku: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.sku == sku).first()
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not found")
    return ProductDetail(
        sku=p.sku,
        name=p.name,
        price=p.price_cents,
        description=p.description,
        category=p.category,
        stockHint=None,
    )
