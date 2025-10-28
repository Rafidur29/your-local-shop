from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from contextlib import contextmanager

DATABASE_URL = settings.DATABASE_URL
engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    # Import models so metadata is available (models will be added in later phases)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("init_db error:", e)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
