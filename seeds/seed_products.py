from app.db import SessionLocal
from app.models import Product

def seed_products():
    db = SessionLocal()
    try:
        products = [
            Product(sku="SKU001", name="Product A", description="First product", price_cents=1200, category="General"),
            Product(sku="SKU002", name="Product B", description="Second product", price_cents=1500, category="General"),
            Product(sku="SKU003", name="Product C", description="Third product", price_cents=1800, category="Premium"),
        ]

        for p in products:
            db.add(p)
        db.commit()
        print("✅ Products seeded successfully!")
    except Exception as e:
        print("❌ Error while seeding:", e)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_products()
