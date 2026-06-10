from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine
from app.firebase_auth import verify_firebase_token

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    firebase_uid = decoded_token["uid"]
    email = decoded_token.get("email")

    if email:
        username = email.split("@")[0]
    else:
        username = f"user_{firebase_uid[:8]}"

    with engine.begin() as connection:
        existing_user = connection.execute(
            text(
                """
                SELECT id, firebase_uid, username, email
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if existing_user:
            return dict(existing_user)

        result = connection.execute(
            text(
                """
                INSERT INTO users (firebase_uid, username, email)
                VALUES (:firebase_uid, :username, :email)
                """
            ),
            {
                "firebase_uid": firebase_uid,
                "username": username,
                "email": email,
            },
        )

        new_user_id = result.lastrowid

        new_user = connection.execute(
            text(
                """
                SELECT id, firebase_uid, username, email
                FROM users
                WHERE id = :id
                """
            ),
            {"id": new_user_id},
        ).mappings().first()

        return dict(new_user)
    
@app.get("/products")
def get_products():
    with engine.connect() as connection:
        products = connection.execute(
            text(
                """
                SELECT
                    id,
                    seller_id,
                    title,
                    description,
                    price,
                    image_url,
                    category,
                    condition_label,
                    status,
                    created_at
                FROM products
                ORDER BY created_at DESC
                """
            )
        ).mappings().all()

    return [dict(product) for product in products]