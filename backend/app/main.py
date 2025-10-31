from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes_catalogue import router as catalogue_router
from app.api.health import router as health_router
from app.db import init_db, SessionLocal
from app.api.routes_cart import router as cart_router
from app.api.routes_inventory import router as inventory_router
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.inventory_service import InventoryService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    init_db()

    # scheduler for expiring reservations
    scheduler = BackgroundScheduler()
    def expire_job():
        db = SessionLocal()
        try:
            svc = InventoryService(db)
            ids = svc.expire_overdue()
            if ids:
                app.logger = getattr(app, "logger", None)
                # optional logging
        finally:
            db.close()
    # run expire_job every 30 seconds
    scheduler.add_job(expire_job, "interval", seconds=30, id="expire_reservations")
    scheduler.start()

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)

app = FastAPI(title="Your Local Shop - Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

app.include_router(catalogue_router, prefix="/api/products", tags=["catalogue"])

app.include_router(cart_router, tags=["cart"])

app.include_router(inventory_router, tags=["inventory"])


