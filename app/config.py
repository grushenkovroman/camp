import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://camp_rasti:camp_rasti@127.0.0.1:5432/camp_rasti",
    )
    ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
    TZ = os.environ.get("TZ", "Europe/Moscow")
