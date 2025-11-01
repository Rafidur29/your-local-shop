import os
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
    Initialize DB schema. In dev you can set RESET_DB=1 to drop & recreate tables.
    Ensure all model modules are imported so metadata is populated.
    """
    if os.environ.get("RESET_DB", "false").lower() in ("1", "true", "yes"):
        print("Resetting database...")
        Base.metadata.drop_all(bind=engine)

    # Ensure models are imported so Base.metadata includes them
    # Add any new model modules here when created.
    try:
        # import side-effects populate Base.metadata
        import app.models.product
        import app.models.inventory_reservation
        import app.models.order
        import app.models.packing_task
        import app.models.shipment
        import app.models.other  # optional / safe to ignore if missing
    except Exception:
        # We intentionally ignore import errors here so init_db won't crash on partial dev changes.
        pass

    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("Database initialized.")
    except Exception as e:
        print("init_db error:", e)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()