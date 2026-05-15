from fastapi import FastAPI
from app.routes.clean_routes import router

app = FastAPI()

app.include_router(router)

from fastapi import FastAPI
from app.routes.clean_routes import router

app = FastAPI()

app.include_router(router)

@app.get("/")

def home():
    return {"message": "Smart Cleaner API Running"}