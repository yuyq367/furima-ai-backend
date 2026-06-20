import json
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

class ProductRecommendationRequest(BaseModel):
    query: str

def row_to_dict(row):
    return dict(row.items())


def rows_to_dicts(rows):
    return [row_to_dict(row) for row in rows]

def build_recommendation_text(product):
    title = product.get("title") or ""
    description = product.get("description") or ""
    category = product.get("category") or ""
    condition_label = product.get("condition_label") or ""
    price = product.get("price")

    price_text = f"{price}円" if price is not None else "未設定"

    return f"""
商品名: {title}
説明: {description}
カテゴリ: {category}
状態: {condition_label}
価格: {price_text}
""".strip()

def cosine_similarity(left_vector, right_vector):
    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left_vector, right_vector)
    )

    left_norm = sum(value * value for value in left_vector) ** 0.5
    right_norm = sum(value * value for value in right_vector) ** 0.5

    if left_norm == 0 or right_norm == 0:
        return 0

    return dot_product / (left_norm * right_norm)

CATEGORY_KEYWORDS = {
    "衣類": ["服", "シャツ", "ニット", "アウター", "パンツ", "スカート", "ワンピース"],
    "靴・バッグ": ["バッグ", "カバン", "鞄", "リュック", "ショルダー", "トート", "靴", "スニーカー"],
    "アクセサリー": ["アクセサリー", "時計", "腕時計", "ネックレス", "リング", "ピアス"],
    "本・漫画": ["本", "漫画", "参考書", "教科書", "小説"],
    "ゲーム・おもちゃ": ["ゲーム", "おもちゃ", "フィギュア"],
    "家電・スマホ": ["家電", "スマホ", "イヤホン", "バッテリー", "充電器", "ガジェット"],
    "インテリア": ["インテリア", "家具", "ライト", "収納"],
    "コスメ・美容": ["コスメ", "美容", "化粧品", "スキンケア"],
    "スポーツ・アウトドア": ["スポーツ", "アウトドア", "キャンプ", "運動"],
    "食品": ["食品", "お菓子", "飲み物"],
    "チケット": ["チケット", "券"],
}


def infer_requested_categories(query):
    matched_categories = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
            matched_categories.append(category)

    return matched_categories


def calculate_recommendation_bonus(query, product):
    requested_categories = infer_requested_categories(query)

    product_category = product.get("category") or ""
    product_text = f"""
{product.get("title") or ""}
{product.get("description") or ""}
{product.get("category") or ""}
{product.get("condition_label") or ""}
""".lower()

    bonus = 0

    if requested_categories:
        if product_category in requested_categories:
            bonus += 0.25
        else:
            bonus -= 0.12

    for category in requested_categories:
        keywords = CATEGORY_KEYWORDS.get(category, [])

        for keyword in keywords:
            if keyword in product_text:
                bonus += 0.08

            if keyword in query and keyword in product_text:
                bonus += 0.12

    return bonus

def build_recommendation_reason(query, product):
    requested_categories = infer_requested_categories(query)
    product_category = product.get("category") or ""
    product_title = product.get("title") or ""

    if requested_categories and product_category in requested_categories:
        return (
            f"「{product_title}」はカテゴリが「{product_category}」で、"
            "入力された条件と関連が強い商品として上位に表示しています。"
        )

    if requested_categories:
        categories_text = "・".join(requested_categories)

        return (
            f"カテゴリは「{categories_text}」とは異なりますが、"
            "商品説明や用途の近さから関連度が高い商品としておすすめしています。"
        )

    return (
        "入力された文章と、商品名・説明文・カテゴリなどの意味的な近さをもとにおすすめしています。"
    )


def build_recommendation_message(query):
    requested_categories = infer_requested_categories(query)

    if requested_categories:
        categories_text = "・".join(requested_categories)

        return (
            f"「{query}」という条件から、{categories_text}に近い商品を中心におすすめしています。"
        )

    return (
        f"「{query}」という条件に対して、商品説明やカテゴリの意味的な近さをもとにおすすめしています。"
    )

def parse_json_text(text):
    cleaned_text = text.strip()

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.removeprefix("```json").strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text.removesuffix("```").strip()

    return json.loads(cleaned_text)


def generate_recommendation_reasons_with_ai(query, products):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        return {}

    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_client = OpenAI(api_key=api_key)

    product_summaries = []

    for product in products:
        product_summaries.append(
            {
                "id": product.get("id"),
                "rank": product.get("recommendation_rank"),
                "title": product.get("title"),
                "description": product.get("description"),
                "price": product.get("price"),
                "category": product.get("category"),
                "condition_label": product.get("condition_label"),
            }
        )

    prompt = f"""
ユーザーはフリマアプリで以下の条件の商品を探しています。

ユーザーの希望:
{query}

AIレコメンドで上位に表示する商品:
{json.dumps(product_summaries, ensure_ascii=False)}

それぞれの商品について、ユーザーにおすすめする理由を日本語で作成してください。

条件:
- 各商品につき1文から2文
- ただのカテゴリ一致の説明にしない
- 商品説明や状態、価格、用途を踏まえて、購入者に魅力が伝わる文章にする
- 誇張しすぎない
- 自然な接客文にする
- 絵文字は使わない
- 必ずJSONだけを返す
- Markdownやコードブロックは使わない

返すJSON形式:
{{
  "reasons": [
    {{
      "id": 商品ID,
      "reason": "おすすめ理由"
    }}
  ]
}}
"""

    try:
        response = openai_client.responses.create(
            model=openai_model,
            instructions="あなたはフリマアプリの商品推薦理由を書くアシスタントです。",
            input=prompt,
        )

        data = parse_json_text(response.output_text)

        reason_by_product_id = {}

        for item in data.get("reasons", []):
            product_id = item.get("id")
            reason = item.get("reason")

            if product_id is None or not reason:
                continue

            reason_by_product_id[int(product_id)] = reason

        return reason_by_product_id

    except Exception as error:
        print(error)
        return {}
    
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
    
@app.post("/ai/product-recommendations")
def recommend_products(request: ProductRecommendationRequest):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="探したい商品の条件を入力してください",
        )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY が設定されていません",
        )

    embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_client = OpenAI(api_key=api_key)

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
                WHERE status = 'available'
                ORDER BY created_at DESC
                """
            )
        ).mappings().all()

    if len(products) == 0:
        return {
            "message": "現在おすすめできる商品がありません。",
            "products": [],
        }

    product_dicts = rows_to_dicts(products)

    recommendation_texts = [f"ユーザーが探している商品: {query}"]

    for product in product_dicts:
        recommendation_texts.append(build_recommendation_text(product))

    try:
        embedding_response = openai_client.embeddings.create(
            model=embedding_model,
            input=recommendation_texts,
        )
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=500,
            detail="商品のレコメンド生成に失敗しました",
        )

    embeddings = [item.embedding for item in embedding_response.data]
    query_embedding = embeddings[0]
    product_embeddings = embeddings[1:]

    recommended_products = []

    for product, product_embedding in zip(product_dicts, product_embeddings):
        embedding_score = cosine_similarity(query_embedding, product_embedding)
        keyword_bonus = calculate_recommendation_bonus(query, product)
        final_score = embedding_score + keyword_bonus

        recommended_product = product.copy()
        recommended_product["recommendation_score"] = round(final_score, 4)

        recommended_products.append(recommended_product)

    recommended_products.sort(
        key=lambda product: product["recommendation_score"],
        reverse=True,
    )

    top_recommended_products = recommended_products[:5]

    for index, product in enumerate(top_recommended_products, start=1):
        product["recommendation_rank"] = index

    ai_reason_by_product_id = generate_recommendation_reasons_with_ai(
        query,
        top_recommended_products,
    )

    for product in top_recommended_products:
        product_id = product["id"]

        product["recommendation_reason"] = ai_reason_by_product_id.get(
            product_id,
        ) or build_recommendation_reason(
            query,
            product,
        )

    return {
        "message": build_recommendation_message(query),
        "products": top_recommended_products,
    }
