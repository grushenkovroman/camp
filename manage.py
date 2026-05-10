#!/usr/bin/env python3
"""Управление приложением: создание схемы, админа и сидинг команд."""
import sys
import secrets
from sqlalchemy import select, text

from app.db import engine, Base, SessionLocal
from app.models import Team, AdminUser
from app.auth import hash_password
from app.config import Config


NEON_PALETTE = [
    "#00ffe1", "#ff2bd6", "#7cff00", "#ffaa00",
    "#5e8aff", "#ff5d5d", "#b66bff", "#00ff88",
    "#ffea00", "#ff0066", "#00b8ff", "#ff8400",
    "#f0ff00", "#00ffae", "#ff00aa", "#69ffff",
]


def create_schema():
    print("→ создаю таблицы…")
    Base.metadata.create_all(engine)
    print("  ok")


def ensure_admin():
    db = SessionLocal()
    try:
        existing = db.execute(
            select(AdminUser).where(AdminUser.login == Config.ADMIN_LOGIN)
        ).scalar_one_or_none()
        if existing:
            print(f"→ админ '{Config.ADMIN_LOGIN}' уже существует")
            return
        admin = AdminUser(
            login=Config.ADMIN_LOGIN,
            password_hash=hash_password(Config.ADMIN_PASSWORD),
        )
        db.add(admin)
        db.commit()
        print(f"→ создан админ: {Config.ADMIN_LOGIN}")
    finally:
        db.close()


def seed_teams():
    db = SessionLocal()
    try:
        existing = db.execute(select(Team)).scalars().all()
        if existing:
            print(f"→ в базе уже {len(existing)} команд, сидинг пропущен")
            return
        for i in range(16):
            team = Team(
                name=f"Команда {i + 1}",
                color=NEON_PALETTE[i],
                sort_order=i,
            )
            db.add(team)
        db.commit()
        print("→ создано 16 команд")
        for t in db.execute(select(Team).order_by(Team.sort_order)).scalars():
            print(f"  {t.name:14} {t.color}  {t.id}")
    finally:
        db.close()


def init():
    create_schema()
    ensure_admin()
    seed_teams()


def reset_admin_password():
    """Сбросить пароль админа на ADMIN_PASSWORD из env."""
    db = SessionLocal()
    try:
        admin = db.execute(
            select(AdminUser).where(AdminUser.login == Config.ADMIN_LOGIN)
        ).scalar_one_or_none()
        if not admin:
            print(f"админ '{Config.ADMIN_LOGIN}' не найден; создаю")
            admin = AdminUser(login=Config.ADMIN_LOGIN, password_hash="")
            db.add(admin)
        admin.password_hash = hash_password(Config.ADMIN_PASSWORD)
        db.commit()
        print(f"→ пароль админа '{Config.ADMIN_LOGIN}' обновлён")
    finally:
        db.close()


def list_teams():
    db = SessionLocal()
    try:
        for t in db.execute(select(Team).order_by(Team.sort_order)).scalars():
            print(f"{t.name:14} {t.color}  {t.id}")
    finally:
        db.close()


def gen_secret():
    print(secrets.token_hex(32))


COMMANDS = {
    "init": init,
    "schema": create_schema,
    "ensure-admin": ensure_admin,
    "seed-teams": seed_teams,
    "reset-admin": reset_admin_password,
    "list-teams": list_teams,
    "gen-secret": gen_secret,
}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd not in COMMANDS:
        print("Использование: manage.py <команда>")
        print("Доступные команды:", ", ".join(COMMANDS))
        sys.exit(1)
    COMMANDS[cmd]()
