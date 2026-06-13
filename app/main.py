import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import text

from app.database import engine
from app.firebase_auth import verify_firebase_token


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://furima-ai-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductCreateRequest(BaseModel):
    title: str
    description: str
    price: int
    image_url: str | None = None
    category: str
    condition_label: str

class ProductUpdateRequest(BaseModel):
    title: str
    description: str
    price: int
    image_url: str | None = None
    category: str
    condition_label: str

class GenerateProductDescriptionRequest(BaseModel):
    title: str
    category: str
    condition_label: str
    price: int | None = None


class GenerateProductDescriptionResponse(BaseModel):
    description: str

def row_to_dict(row):
    return dict(row.items())


def rows_to_dicts(rows):
    return [row_to_dict(row) for row in rows]


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

        if existing_user is not None:
            return row_to_dict(existing_user)

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

        if new_user is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to create user",
            )

        return row_to_dict(new_user)


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

    return rows_to_dicts(products)


@app.post("/products")
def create_product(
    request: ProductCreateRequest,
    decoded_token: dict = Depends(verify_firebase_token),
):
    firebase_uid = decoded_token["uid"]

    with engine.begin() as connection:
        user = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

        result = connection.execute(
            text(
                """
                INSERT INTO products (
                    seller_id,
                    title,
                    description,
                    price,
                    image_url,
                    category,
                    condition_label
                )
                VALUES (
                    :seller_id,
                    :title,
                    :description,
                    :price,
                    :image_url,
                    :category,
                    :condition_label
                )
                """
            ),
            {
                "seller_id": user["id"],
                "title": request.title,
                "description": request.description,
                "price": request.price,
                "image_url": request.image_url,
                "category": request.category,
                "condition_label": request.condition_label,
            },
        )

        new_product_id = result.lastrowid

        product = connection.execute(
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
                WHERE id = :id
                """
            ),
            {"id": new_product_id},
        ).mappings().first()

        if product is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to create product",
            )

        return row_to_dict(product)


@app.get("/products/{product_id}")
def get_product(product_id: int):
    with engine.connect() as connection:
        product = connection.execute(
            text(
                """
                SELECT
                    products.id,
                    products.seller_id,
                    products.title,
                    products.description,
                    products.price,
                    products.image_url,
                    products.category,
                    products.condition_label,
                    products.status,
                    products.created_at,
                    users.username AS seller_username
                FROM products
                JOIN users
                    ON products.seller_id = users.id
                WHERE products.id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return row_to_dict(product)

@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    request: ProductUpdateRequest,
    decoded_token: dict = Depends(verify_firebase_token),
):
    firebase_uid = decoded_token["uid"]

    title = request.title.strip()
    description = request.description.strip()
    category = request.category.strip()
    condition_label = request.condition_label.strip()
    image_url = request.image_url.strip() if request.image_url else None

    if not title:
        raise HTTPException(status_code=400, detail="商品名を入力してください")

    if not description:
        raise HTTPException(status_code=400, detail="商品説明を入力してください")

    if request.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="価格は1円以上で入力してください",
        )

    if not category:
        raise HTTPException(status_code=400, detail="カテゴリを選択してください")

    if not condition_label:
        raise HTTPException(status_code=400, detail="商品の状態を選択してください")

    with engine.begin() as connection:
        user = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

        product = connection.execute(
            text(
                """
                SELECT id, seller_id
                FROM products
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        if product["seller_id"] != user["id"]:
            raise HTTPException(
                status_code=403,
                detail="You can only update your own product",
            )

        connection.execute(
            text(
                """
                UPDATE products
                SET
                    title = :title,
                    description = :description,
                    price = :price,
                    image_url = :image_url,
                    category = :category,
                    condition_label = :condition_label
                WHERE id = :product_id
                """
            ),
            {
                "product_id": product_id,
                "title": title,
                "description": description,
                "price": request.price,
                "image_url": image_url,
                "category": category,
                "condition_label": condition_label,
            },
        )

        updated_product = connection.execute(
            text(
                """
                SELECT
                    products.id,
                    products.seller_id,
                    products.title,
                    products.description,
                    products.price,
                    products.image_url,
                    products.category,
                    products.condition_label,
                    products.status,
                    products.created_at,
                    users.username AS seller_username
                FROM products
                JOIN users
                    ON products.seller_id = users.id
                WHERE products.id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if updated_product is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to update product",
            )

        return row_to_dict(updated_product)

@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    decoded_token: dict = Depends(verify_firebase_token),
):
    firebase_uid = decoded_token["uid"]

    with engine.begin() as connection:
        user = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

        product = connection.execute(
            text(
                """
                SELECT id, seller_id, status
                FROM products
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        if product["seller_id"] != user["id"]:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own product",
            )

        if product["status"] == "sold":
            raise HTTPException(
                status_code=400,
                detail="Sold products cannot be deleted",
            )

        purchase = connection.execute(
            text(
                """
                SELECT id
                FROM purchases
                WHERE product_id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if purchase is not None:
            raise HTTPException(
                status_code=400,
                detail="Purchased products cannot be deleted",
            )

        connection.execute(
            text(
                """
                DELETE FROM products
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        )

        return {"message": "Product deleted"}

@app.post("/products/{product_id}/purchase")
def purchase_product(
    product_id: int,
    decoded_token: dict = Depends(verify_firebase_token),
):
    firebase_uid = decoded_token["uid"]

    with engine.begin() as connection:
        buyer = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if buyer is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

        product = connection.execute(
            text(
                """
                SELECT id, seller_id, status
                FROM products
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

        if product["status"] == "sold":
            raise HTTPException(
                status_code=400,
                detail="Product is already sold",
            )

        if product["seller_id"] == buyer["id"]:
            raise HTTPException(
                status_code=400,
                detail="You cannot purchase your own product",
            )

        connection.execute(
            text(
                """
                INSERT INTO purchases (product_id, buyer_id)
                VALUES (:product_id, :buyer_id)
                """
            ),
            {
                "product_id": product_id,
                "buyer_id": buyer["id"],
            },
        )

        connection.execute(
            text(
                """
                UPDATE products
                SET status = 'sold'
                WHERE id = :product_id
                """
            ),
            {"product_id": product_id},
        )

        purchase = connection.execute(
            text(
                """
                SELECT
                    purchases.id,
                    purchases.product_id,
                    purchases.buyer_id,
                    purchases.purchased_at,
                    products.status
                FROM purchases
                JOIN products
                    ON purchases.product_id = products.id
                WHERE purchases.product_id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().first()

        if purchase is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to create purchase",
            )

        return row_to_dict(purchase)


@app.get("/users/me/products")
def get_my_products(decoded_token: dict = Depends(verify_firebase_token)):
    firebase_uid = decoded_token["uid"]

    with engine.connect() as connection:
        user = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

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
                WHERE seller_id = :seller_id
                ORDER BY created_at DESC
                """
            ),
            {"seller_id": user["id"]},
        ).mappings().all()

    return rows_to_dicts(products)


@app.get("/users/me/purchases")
def get_my_purchases(decoded_token: dict = Depends(verify_firebase_token)):
    firebase_uid = decoded_token["uid"]

    with engine.connect() as connection:
        user = connection.execute(
            text(
                """
                SELECT id
                FROM users
                WHERE firebase_uid = :firebase_uid
                """
            ),
            {"firebase_uid": firebase_uid},
        ).mappings().first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User is not registered in database",
            )

        purchases = connection.execute(
            text(
                """
                SELECT
                    purchases.id AS purchase_id,
                    purchases.product_id,
                    purchases.buyer_id,
                    purchases.purchased_at,
                    products.seller_id,
                    products.title,
                    products.description,
                    products.price,
                    products.image_url,
                    products.category,
                    products.condition_label,
                    products.status,
                    products.created_at,
                    users.username AS seller_username
                FROM purchases
                JOIN products
                    ON purchases.product_id = products.id
                JOIN users
                    ON products.seller_id = users.id
                WHERE purchases.buyer_id = :buyer_id
                ORDER BY purchases.purchased_at DESC
                """
            ),
            {"buyer_id": user["id"]},
        ).mappings().all()

    return rows_to_dicts(purchases)

@app.post(
    "/ai/product-description",
    response_model=GenerateProductDescriptionResponse,
)
def generate_product_description(request: GenerateProductDescriptionRequest):
    title = request.title.strip()
    category = request.category.strip()
    condition_label = request.condition_label.strip()

    if not title:
        raise HTTPException(status_code=400, detail="商品名を入力してください")

    if not category:
        raise HTTPException(status_code=400, detail="カテゴリを選択してください")

    if not condition_label:
        raise HTTPException(status_code=400, detail="商品の状態を選択してください")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY が設定されていません",
        )

    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_client = OpenAI(api_key=api_key)

    price_text = (
        f"{request.price:,}円"
        if request.price is not None and request.price > 0
        else "未設定"
    )

    prompt = f"""
以下の商品情報をもとに、フリマアプリの商品説明文を日本語で作成してください。

条件:
- 120文字から200文字程度
- 誇張しすぎない
- 丁寧で自然な文章
- 購入者が知りたい情報が伝わる文章
- 絵文字は使わない
- 商品説明文だけを出力する
- 箇条書きではなく文章で書く

商品情報:
商品名: {title}
カテゴリ: {category}
商品の状態: {condition_label}
価格: {price_text}
"""

    try:
        response = openai_client.responses.create(
            model=openai_model,
            instructions="あなたはフリマアプリの商品説明文を作るアシスタントです。",
            input=prompt,
        )

        description = response.output_text.strip()

        if not description:
            raise HTTPException(
                status_code=500,
                detail="説明文を生成できませんでした",
            )

        return GenerateProductDescriptionResponse(description=description)

    except HTTPException:
        raise
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=500,
            detail="AI説明文の生成に失敗しました",
        )