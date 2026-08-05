from fastapi import FastAPI

# Database
from app.db.database import engine
from app.db.base import Base

# Import all models so SQLAlchemy registers every table
import app.models.users
import app.models.restaurant
import app.models.menu_category   # NEW

# Routers
from app.api.auth import router as auth_router
from app.api.restaurant import router as restaurant_router
from app.api.menu_category import router as menu_category_router

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0",
)

# Register API routers
app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(menu_category_router)   # NEW


# ------------------------------------------------------------------
# Root Endpoint
# ------------------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to SmartFoodOps API"
    }


# ------------------------------------------------------------------
# Health Check
# ------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ------------------------------------------------------------------
# Identify Endpoint
# ------------------------------------------------------------------
@app.get("/identify")
def identify_me():
    return {
        "name": "arsam"
    }