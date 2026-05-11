import uuid
from flask import Blueprint, render_template, abort, request
from sqlalchemy import select, func, or_, and_

from .db import SessionLocal
from .models import (
    Team,
    ScoreEvent,
    DailyTask,
    Shift,
    ScheduleBlock,
    RotationSlot,
    Activity,
)
from .utils import today_local, parse_date, shift_date, day_index, day_label

bp = Blueprint("public", __name__)


@bp.get("/<uuid:team_uuid>")
def team_page(team_uuid: uuid.UUID):
    db = SessionLocal()
    try:
        team = db.get(Team, team_uuid)
        if not team:
            abort(404)

        selected = parse_date(request.args.get("date")) or today_local()

        events_today = db.execute(
            select(ScoreEvent)
            .where(ScoreEvent.team_id == team.id, ScoreEvent.event_date == selected)
            .order_by(ScoreEvent.created_at.desc())
        ).scalars().all()

        total_today = sum(e.points for e in events_today)

        total_all = db.execute(
            select(func.coalesce(func.sum(ScoreEvent.points), 0)).where(
                ScoreEvent.team_id == team.id
            )
        ).scalar_one()

        task = db.get(DailyTask, selected)

        members = [m for m in team.members if m.role == "member"]
        mentors = [m for m in team.members if m.role == "mentor"]

        return render_template(
            "public/team.html",
            team=team,
            selected=selected,
            prev_date=shift_date(selected, -1),
            next_date=shift_date(selected, 1),
            today=today_local(),
            events=events_today,
            total_today=total_today,
            total_all=total_all,
            task=task,
            members=members,
            mentors=mentors,
        )
    finally:
        db.close()


@bp.get("/<uuid:team_uuid>/schedule")
def team_schedule(team_uuid: uuid.UUID):
    db = SessionLocal()
    try:
        team = db.get(Team, team_uuid)
        if not team:
            abort(404)

        selected = parse_date(request.args.get("date")) or today_local()
        shift = db.get(Shift, 1)
        d_idx = day_index(shift, selected) if shift else None
        d_label = day_label(shift, selected) if shift else None

        # блоки расписания, применимые для этой команды + дня
        blocks = []
        items = []
        if d_idx is not None:
            stmt = select(ScheduleBlock).where(
                or_(
                    ScheduleBlock.only_for_team_id == None,  # noqa: E711
                    ScheduleBlock.only_for_team_id == team.id,
                )
            ).order_by(ScheduleBlock.block_time, ScheduleBlock.sort_order)
            for b in db.execute(stmt).scalars():
                if d_idx not in (b.active_days or []):
                    continue
                # для К0 (in_rotation=False) пропускаем rotation-якори
                if b.kind == "rotation" and not team.in_rotation:
                    continue
                # team-specific блок другой команды не должен попасть
                if b.only_for_team_id is not None and b.only_for_team_id != team.id:
                    continue
                blocks.append(b)

            # активности из ротации (только если команда в ротации)
            rotation_map = {}
            if team.in_rotation:
                rows = db.execute(
                    select(RotationSlot).where(
                        RotationSlot.team_id == team.id,
                        RotationSlot.day_index == d_idx,
                    )
                ).scalars().all()
                rotation_map = {r.slot_position: r for r in rows}

            for b in blocks:
                if b.kind == "rotation" and b.rotation_slot is not None:
                    rs = rotation_map.get(b.rotation_slot)
                    if rs and rs.activity_id:
                        act = db.get(Activity, rs.activity_id)
                        items.append({
                            "time": b.block_time,
                            "icon": act.icon if act else b.icon,
                            "title": act.name if act else b.title,
                            "description": (act.description if act else b.description),
                            "place": act.place if act else "",
                            "is_rotation": True,
                        })
                    else:
                        items.append({
                            "time": b.block_time,
                            "icon": b.icon,
                            "title": "—",
                            "description": b.description,
                            "place": "",
                            "is_rotation": True,
                        })
                else:
                    items.append({
                        "time": b.block_time,
                        "icon": b.icon,
                        "title": b.title,
                        "description": b.description,
                        "place": "",
                        "is_rotation": False,
                    })

        return render_template(
            "public/schedule.html",
            team=team,
            selected=selected,
            prev_date=shift_date(selected, -1),
            next_date=shift_date(selected, 1),
            today=today_local(),
            day_label_text=d_label,
            items=items,
            in_shift=(d_idx is not None),
        )
    finally:
        db.close()


@bp.get("/")
def index():
    abort(404)
