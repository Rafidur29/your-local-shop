import json
import argparse
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.db import Base, engine, SessionLocal
from app.repositories.product_repo import ProductRepository
# Ensure models imported so tables created:
from app.models.product import Product  # noqa: F401

def seed_from_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()
    repo = ProductRepository(db)
    try:
        for entry in data:
            sku = entry.get("sku") or entry.get("id") or entry.get("productId")
            name = entry.get("name") or entry.get("title", "")
            price = int(entry.get("price_cents") if entry.get("price_cents") is not None else int(float(entry.get("price",0))*100))
            stock = int(entry.get("stock", entry.get("quantity", 0)))
            description = entry.get("description", "")
            image = entry.get("image") or (entry.get("images")[0] if entry.get("images") else None)
            repo.create_or_update(sku=sku, name=name, price_cents=price, stock=stock, description=description, image=image)
        db.commit()
        print("Seeded products:", len(data))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", "-f", default="../public/mock/catalogue.json", help="Path to product json (frontend mock)")
    args = p.parse_args()
    if not os.path.exists(args.file):
        print("File not found:", args.file)
        exit(1)
    seed_from_file(args.file)
