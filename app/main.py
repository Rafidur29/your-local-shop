from fastapi import FastAPI
from .db import Base, engine
from .routers import products, cart, admin

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize the FastAPI app
app = FastAPI(title="E-Commerce Backend (Sith scope)")

# Include routers
app.include_router(products.router)
app.include_router(cart.router)
app.include_router(admin.router)

# Root endpoint
@app.get("/")
def root():
    return {"service": "ok"}
