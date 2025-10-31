from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.orm import Session
from app.db import get_db
from app.repositories.product_repo import ProductRepository
from app.schemas.product_schema import ProductOut

router = APIRouter(tags=["catalogue"])

@router.get("", summary="List products")
def list_products(
    q: Optional[str] = Query(None, description="search term"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    repo = ProductRepository(db)
    items, total = repo.list(q=q, page=page, size=size)
    items_out = [ProductOut.model_validate(p).model_dump() for p in items]
    return {"items": items_out, "page": page, "size": size, "total": total}

@router.get("/{sku}", summary="Get product by SKU")
def get_product(sku: str, db: Session = Depends(get_db)):
    repo = ProductRepository(db)
    p = repo.get_by_sku(sku)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut.model_validate(p).model_dump()
