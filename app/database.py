import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME")


if not DB_NAME:
    raise RuntimeError("DB_NAME is not set")

if not DB_USER:
    raise RuntimeError("DB_USER is not set")

if not DB_PASSWORD:
    raise RuntimeError("DB_PASSWORD is not set")


if INSTANCE_CONNECTION_NAME:
    DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        query={
            "unix_socket": f"/cloudsql/{INSTANCE_CONNECTION_NAME}",
        },
    )
else:
    if not DB_HOST:
        raise RuntimeError("DB_HOST is not set")

    DATABASE_URL = URL.create(
        drivername="mysql+pymysql",
        username=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)