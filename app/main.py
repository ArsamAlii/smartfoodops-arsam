from fastapi import FastAPI

from app.db.database import engine
from app.db.base import Base

import app.models.users
import app.models.restaurant
import app.models.menu_category
import app.models.menu_item

from app.api.auth import router as auth_router
from app.api.restaurant import router as restaurant_router
from app.api.menu_category import router as menu_category_router
from app.api.menu_item import router as menu_item_router

# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0",
)

app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(menu_category_router)
app.include_router(menu_item_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to SmartFoodOps API"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/identify")
def identify_me():
    return {
        "name": "arsam"
    }