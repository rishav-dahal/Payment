from fastapi import FastAPI

app = FastAPI(
    title="Payment Service API",
    description="API for Unified Payments - Manage payment transactions and processors",
    version="1.0.0",
)


@app.get("/")
def server_root():
    return {"message": "payment service is running"}