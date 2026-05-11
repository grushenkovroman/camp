#!/usr/bin/env python3
"""Управление приложением: создание схемы, админа и сидинг команд."""
import sys
import secrets
from datetime import date, time
from sqlalchemy import select, text, func

from app.db import engine, Base, SessionLocal
from app.models import (
    Team,
    AdminUser,
    Shift,
    Activity,
    ScheduleBlock,
    RotationSlot,
)
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
    # доп. ALTER для уже существующих таблиц (idempotent)
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE teams ADD COLUMN IF NOT EXISTS in_rotation BOOLEAN NOT NULL DEFAULT TRUE"
        ))
        conn.commit()
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


def seed_shift():
    """Создать запись смены, если ещё нет."""
    db = SessionLocal()
    try:
        existing = db.get(Shift, 1)
        if existing:
            print(f"→ смена уже задана: {existing.start_date}, {existing.total_days} дн.")
            return
        db.add(Shift(
            id=1,
            start_date=date(2026, 5, 11),
            total_days=8,
            name="Путь надежды",
        ))
        db.commit()
        print("→ создана смена: 2026-05-11, 8 дн., «Путь надежды»")
    finally:
        db.close()


def seed_schedule():
    """Засеять каталог активностей, блоки расписания и матрицу ротации."""
    from app.seed_data import (
        SCHEDULE_BLOCKS,
        ACTIVITIES,
        ROTATION,
        ACTIVITY_NAME_MAP,
    )

    db = SessionLocal()
    try:
        # 1. activities
        existing_acts = {a.name: a for a in db.execute(select(Activity)).scalars()}
        if existing_acts:
            print(f"→ активности уже есть: {len(existing_acts)}, сидинг пропущен")
        else:
            for i, (name, desc, place, icon) in enumerate(ACTIVITIES):
                db.add(Activity(
                    name=name, description=desc, place=place, icon=icon, sort_order=i,
                ))
            db.commit()
            existing_acts = {a.name: a for a in db.execute(select(Activity)).scalars()}
            print(f"→ создано активностей: {len(existing_acts)}")

        # 2. schedule blocks
        n_blocks = db.execute(select(ScheduleBlock)).scalars().first()
        if n_blocks:
            print("→ блоки расписания уже есть, сидинг пропущен")
        else:
            for i, (t, icon, title, desc, kind, rot_slot, days) in enumerate(SCHEDULE_BLOCKS):
                db.add(ScheduleBlock(
                    sort_order=i,
                    block_time=t,
                    icon=icon,
                    title=title,
                    description=desc,
                    active_days=days,
                    kind=kind,
                    rotation_slot=rot_slot,
                ))
            db.commit()
            print(f"→ создано блоков расписания: {len(SCHEDULE_BLOCKS)}")

        # 3. К0: in_rotation=False, и кастомные блоки 10/11/12 для неё
        k0 = db.execute(
            select(Team).where(Team.name == "Команда 0")
        ).scalar_one_or_none()
        if k0:
            if k0.in_rotation:
                k0.in_rotation = False
                db.commit()
                print("→ К0: in_rotation выключен")
            # кастомные блоки К0 (заглушки — админ заполнит)
            has_k0_blocks = db.execute(
                select(ScheduleBlock).where(ScheduleBlock.only_for_team_id == k0.id)
            ).scalars().first()
            if not has_k0_blocks:
                for i, t in enumerate([time(10, 0), time(11, 0), time(12, 0)]):
                    db.add(ScheduleBlock(
                        sort_order=100 + i,
                        block_time=t,
                        icon="✨",
                        title="(не задано)",
                        description="",
                        active_days=list(range(1, 7)),
                        kind="fixed",
                        rotation_slot=None,
                        only_for_team_id=k0.id,
                    ))
                db.commit()
                print("→ К0: добавлены 3 кастомных блока 10/11/12 (заглушки)")

        # 4. матрица ротации
        n_existing_rot = db.execute(
            select(func.count()).select_from(RotationSlot)
        ).scalar_one()
        if n_existing_rot > 0:
            print(f"→ ротация уже заполнена ({n_existing_rot} записей), сидинг пропущен")
            return

        # порядок команд К1..К16 — берём по sort_order, исключая К0
        teams = db.execute(
            select(Team).where(Team.name != "Команда 0").order_by(Team.sort_order)
        ).scalars().all()
        if len(teams) != 16:
            print(f"⚠ ожидалось 16 команд (без К0), нашёл {len(teams)} — пропускаю ротацию")
            return

        created = 0
        for day_idx, slots in ROTATION.items():
            for slot_pos, row in enumerate(slots):
                for team_i, raw_name in enumerate(row):
                    canonical = ACTIVITY_NAME_MAP.get(raw_name.strip(), None)
                    if canonical is None:
                        print(f"⚠ неизвестная активность в CSV: '{raw_name}'")
                        continue
                    activity = existing_acts.get(canonical)
                    if not activity:
                        print(f"⚠ активность '{canonical}' нет в БД")
                        continue
                    db.add(RotationSlot(
                        team_id=teams[team_i].id,
                        day_index=day_idx,
                        slot_position=slot_pos,
                        activity_id=activity.id,
                    ))
                    created += 1
        db.commit()
        print(f"→ создано записей ротации: {created}")
    finally:
        db.close()


def init():
    create_schema()
    ensure_admin()
    seed_teams()
    seed_shift()
    seed_schedule()


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
    "seed-shift": seed_shift,
    "seed-schedule": seed_schedule,
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
