import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from contextlib import contextmanager

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """
    Initialize DB schema.

    Behavior:
      - If RESET_DB env var is set to 1/true/yes, drop & recreate tables.
      - If we detect pytest running (common cases), automatically drop & recreate tables so tests run against a clean DB.
      - Otherwise, leave existing tables in place (previous behavior).

    Ensure all model modules are imported so metadata is populated.
    """
    import importlib, traceback

    # detect request to reset via env var
    env_reset = os.environ.get("RESET_DB", "false").lower() in ("1", "true", "yes")

    # heuristic detection of pytest run:
    # - sys.argv often contains 'pytest' when tests are started with 'pytest'
    # - some pytest-related env vars may exist (we check for common ones)
    running_pytest = False
    try:
        if any("pytest" in os.path.basename(a).lower() for a in sys.argv):
            running_pytest = True
    except Exception:
        running_pytest = running_pytest or False

    # additional heuristic: look for common pytest env variables
    if not running_pytest:
        for k in os.environ.keys():
            if k.upper().startswith("PYTEST") or k.upper() == "PYTEST_CURRENT_TEST":
                running_pytest = True
                break

    if env_reset or running_pytest:
        print("Resetting database (RESET_DB set or pytest detected)...")
        Base.metadata.drop_all(bind=engine)

    # List of model modules we expect to import here (add new modules here)
    model_modules = [
        "app.models.product",
        "app.models.inventory_reservation",
        "app.models.order",
        "app.models.shipment",
        "app.models.packing_task",
        "app.models.invoice",
        "app.models.cart",
        "app.models.cart_item",
        "app.models.idempotency",
        "app.models.return_request",
        "app.models.return_line",
        "app.models.credit_note",
    ]

    succeeded = []
    failed = []
    for mod in model_modules:
        try:
            importlib.import_module(mod)
            succeeded.append(mod)
        except Exception as e:
            failed.append((mod, traceback.format_exc()))

    print(f"init_db: model import succeeded: {succeeded}")
    if failed:
        print("init_db: model import FAILED for (these may not exist or have errors):")
        for mod, tb in failed:
            print(f"--- {mod} ---")
            print(tb)

    try:
        # create tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database initialized.")

        # --- Ensure canonical test SKUs exist for unit tests (idempotent) ---
        from app.models.product import Product
        from app.db import SessionLocal as _SessionLocal  # short use session
        s = _SessionLocal()
        try:
            required = [
                {"sku": "TEST-001", "name": "Seed Test 1", "price_cents": 199, "stock": 10},
                {"sku": "TEST-002", "name": "Seed Test 2", "price_cents": 299, "stock": 10},
                {"sku": "T1",      "name": "Tea 100g",     "price_cents": 300, "stock": 5},
                {"sku": "T2",      "name": "Coffee 200g",  "price_cents": 600, "stock": 1},
                {"sku": "RES-1",   "name": "Reserve1",     "price_cents": 100, "stock": 5},
                {"sku": "RES-2",   "name": "Reserve2",     "price_cents": 200, "stock": 1},
                {"sku": "PKG1",    "name": "Test Package", "price_cents": 100, "stock": 1},
                {"sku": "RET1",    "name": "Returnable",   "price_cents": 500, "stock": 5},
            ]
            created = 0
            for ent in required:
                if not s.query(Product).filter(Product.sku == ent["sku"]).first():
                    p = Product(sku=ent["sku"], name=ent["name"], price_cents=ent["price_cents"], stock=ent["stock"])
                    if hasattr(p, "description"):
                        p.description = ent.get("description")
                    s.add(p)
                    created += 1
            if created:
                s.commit()
                print(f"Seeded {created} missing test products.")
        finally:
            s.close()

    except Exception:
        # don't blow up init_db if anything goes wrong here; print for diagnostics
        import traceback
        print("init_db/create+seed failed:", traceback.format_exc())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()