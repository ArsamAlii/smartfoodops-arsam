from fastapi import FastAPI

app = FastAPI(
    title="SmartFoodOps API",
    version="1.0.0"
)


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
    return{
        "name" : "arsam"
    }