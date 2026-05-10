import uuid
from flask import Blueprint, render_template, abort, request
from sqlalchemy import select, func

from .db import SessionLocal
from .models import Team, ScoreEvent, DailyTask
from .utils import today_local, parse_date, shift_date

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


@bp.get("/")
def index():
    abort(404)
