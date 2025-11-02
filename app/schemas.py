from pydantic import BaseModel, Field
from typing import List, Optional


class ProductListItem(BaseModel):
    sku: str
    name: str
    price: int = Field(alias="price_cents")
    stockHint: Optional[int] = None

    class Config:
        populate_by_name = True


class ProductDetail(ProductListItem):
    description: Optional[str] = None
    category: Optional[str] = None


class PaginatedProducts(BaseModel):
    items: List[ProductListItem]
    page: int
    size: int
    total: int


class CartItemIn(BaseModel):
    sku: str
    qty: int


class CartItemOut(BaseModel):
    id: int
    sku: str
    qty: int
    price_snapshot: int


class CartOut(BaseModel):
    items: List[CartItemOut]
    totals: dict
    reservationInfo: Optional[dict] = None
