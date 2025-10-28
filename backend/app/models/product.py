from sqlalchemy import Column, Integer, String, Boolean, Text
from app.db import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    image = Column(String(512), nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    stock = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<Product sku={self.sku} name={self.name}>"
