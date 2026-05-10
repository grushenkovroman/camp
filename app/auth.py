import bcrypt
from flask_login import LoginManager, UserMixin
from sqlalchemy import select

from .db import SessionLocal
from .models import AdminUser


login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message = "Войдите, чтобы продолжить."


class AuthUser(UserMixin):
    def __init__(self, admin: AdminUser):
        self.id = str(admin.id)
        self.login = admin.login


@login_manager.user_loader
def load_user(user_id: str):
    db = SessionLocal()
    try:
        admin = db.get(AdminUser, int(user_id))
        return AuthUser(admin) if admin else None
    finally:
        db.close()


def verify_password(login: str, password: str) -> AuthUser | None:
    db = SessionLocal()
    try:
        admin = db.execute(
            select(AdminUser).where(AdminUser.login == login)
        ).scalar_one_or_none()
        if not admin:
            return None
        if bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
            return AuthUser(admin)
        return None
    finally:
        db.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
