from fastapi import FastAPI
from sqlalchemy import text

from app.database import engine

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Hello, Furima AI"}


@app.get("/health/db")
def check_db_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar()

    return {"db": "connected", "result": value}