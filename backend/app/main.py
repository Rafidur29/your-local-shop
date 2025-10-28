from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes_catalogue import router as catalogue_router
from app.api.health import router as health_router
from app.db import init_db

app = FastAPI(title="Your Local Shop - Backend (Phase 0)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)

app.include_router(catalogue_router, prefix="/api/products", tags=["catalogue"])

@app.on_event("startup")
def on_startup():
    init_db()
