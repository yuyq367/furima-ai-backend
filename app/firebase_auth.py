import os

import firebase_admin
from dotenv import load_dotenv
from fastapi import Header, HTTPException
from firebase_admin import auth, credentials

load_dotenv()

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")


def initialize_firebase():
    if firebase_admin._apps:
        return

    if not FIREBASE_PROJECT_ID:
        raise RuntimeError("FIREBASE_PROJECT_ID is not set")

    cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(
        cred,
        {
            "projectId": FIREBASE_PROJECT_ID,
        },
    )


def verify_firebase_token(authorization: str | None = Header(default=None)):
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is missing",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header",
        )

    id_token = authorization.replace("Bearer ", "")

    try:
        initialize_firebase()
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Firebase token",
        )