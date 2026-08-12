from fastapi import FastAPI
from app.api.payments import router as payments_router
from app.db.database import engine
from app.db.base import Base
from app.api.orders import router as orders_router
# -------------------------------------------------------
# Models
# -------------------------------------------------------
import app.models.users
import app.models.restaurant
import app.models.menu_category
import app.models.menu_item
import app.models.order
import app.models.order_item
import app.models.order_status_history
import app.models.payment

# -------------------------------------------------------
# API Routers
# -------------------------------------------------------
from app.api.auth import router as auth_router
from app.api.restaurant import router as restaurant_router
from app.api.menu_category import router as menu_category_router
from app.api.menu_item import router as menu_item_router
from app.api.orders import router as orders_router
from app.api.users import router as users_router

# Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0",
)


# -------------------------------------------------------
# Routers
# -------------------------------------------------------
app.include_router(auth_router)
app.include_router(restaurant_router)
app.include_router(menu_category_router)
app.include_router(menu_item_router)
app.include_router(orders_router)
app.include_router(payments_router)
app.include_router(users_router)
# -------------------------------------------------------
# Root
# -------------------------------------------------------
@app.get("/")
def root():
    return {
        "message": "Welcome to SmartFoodOps API"
    }


# -------------------------------------------------------
# Health
# -------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# -------------------------------------------------------
# Identify
# -------------------------------------------------------
@app.get("/identify")
def identify_me():
    return {
        "name": "arsam"
    }
