from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def server_root():
    return {"message": "payment service is running"}