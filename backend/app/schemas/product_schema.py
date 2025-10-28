# backend/app/schemas/product_schema.py
from typing import Optional
from pydantic import BaseModel
from pydantic import ConfigDict

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    sku: str
    name: str
    description: Optional[str] = None
    price_cents: int
    image: Optional[str] = None
    stock: int
    active: bool
