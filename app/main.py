from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.db.database import engine
from app.db.base import Base

# Import all models so SQLAlchemy knows about them
import app.db.base  # or app.models if that's where all models are imported

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0"
)

app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "Welcome to SmartFoodOps API"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/identify")
def identify_me():
    return {"name": "arsam"}