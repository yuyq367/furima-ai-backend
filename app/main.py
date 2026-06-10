from fastapi import Depends, FastAPI
from sqlalchemy import text

from app.database import engine
from app.firebase_auth import verify_firebase_token

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

@app.get("/auth/me")
def get_current_user(decoded_token: dict = Depends(verify_firebase_token)):
    return {
        "firebase_uid": decoded_token["uid"],
        "email": decoded_token.get("email"),
        "name": decoded_token.get("name"),
    }