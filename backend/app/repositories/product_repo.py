from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.product import Product

class ProductRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_sku(self, sku: str) -> Optional[Product]:
        return self.db.query(Product).filter(Product.sku == sku, Product.active == True).first()

    def list(self, q: Optional[str] = None, page: int = 1, size: int = 20) -> Tuple[List[Product], int]:
        query = self.db.query(Product).filter(Product.active == True)
        if q:
            like = f"%{q}%"
            query = query.filter((Product.name.ilike(like)) | (Product.description.ilike(like)))
        total = query.with_entities(func.count()).scalar() or 0
        items = query.order_by(Product.name).offset((page - 1) * size).limit(size).all()
        return items, total

    def create_or_update(self, sku: str, name: str, price_cents: int, stock: int = 0, description: str = None, image: str = None):
        p = self.db.query(Product).filter(Product.sku == sku).first()
        if p:
            p.name = name
            p.price_cents = price_cents
            p.stock = stock
            p.description = description
            p.image = image
        else:
            p = Product(sku=sku, name=name, price_cents=price_cents, stock=stock, description=description, image=image)
            self.db.add(p)
        self.db.flush()
        return p
