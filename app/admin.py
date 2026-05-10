import uuid
from datetime import date
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import select, func

from .db import SessionLocal
from .models import Team, TeamMember, ScoreEvent, DailyTask
from .auth import verify_password
from .utils import today_local, parse_date


bp = Blueprint("admin", __name__, url_prefix="/admin")


# --- auth ---------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        user = verify_password(login_value, password)
        if user:
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Неверный логин или пароль", "error")
    return render_template("admin/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


# --- dashboard ----------------------------------------------------------

@bp.get("/")
@login_required
def dashboard():
    db = SessionLocal()
    try:
        teams = db.execute(
            select(Team).order_by(Team.sort_order, Team.name)
        ).scalars().all()

        # totals
        rows = db.execute(
            select(ScoreEvent.team_id, func.coalesce(func.sum(ScoreEvent.points), 0))
            .group_by(ScoreEvent.team_id)
        ).all()
        totals = {tid: total for tid, total in rows}

        selected = parse_date(request.args.get("date")) or today_local()
        task = db.get(DailyTask, selected)

        return render_template(
            "admin/dashboard.html",
            teams=teams,
            totals=totals,
            today=today_local(),
            selected=selected,
            task=task,
        )
    finally:
        db.close()


# --- teams --------------------------------------------------------------

@bp.get("/teams/<team_id>")
@login_required
def team_edit(team_id):
    db = SessionLocal()
    try:
        team = db.get(Team, uuid.UUID(team_id))
        if not team:
            abort(404)
        return render_template("admin/team_edit.html", team=team)
    finally:
        db.close()


@bp.post("/teams/<team_id>")
@login_required
def team_update(team_id):
    db = SessionLocal()
    try:
        team = db.get(Team, uuid.UUID(team_id))
        if not team:
            abort(404)
        team.name = request.form.get("name", team.name).strip() or team.name
        team.color = request.form.get("color", team.color).strip() or team.color

        # rebuild members from form
        # form fields: member_name[], mentor_name[]
        member_names = [n.strip() for n in request.form.getlist("member_name") if n.strip()]
        mentor_names = [n.strip() for n in request.form.getlist("mentor_name") if n.strip()]

        team.members.clear()
        db.flush()
        for i, name in enumerate(member_names):
            team.members.append(TeamMember(name=name, role="member", sort_order=i))
        for i, name in enumerate(mentor_names):
            team.members.append(TeamMember(name=name, role="mentor", sort_order=i))

        db.commit()
        flash("Команда сохранена", "ok")
        return redirect(url_for("admin.team_edit", team_id=team_id))
    finally:
        db.close()


# --- scores -------------------------------------------------------------

@bp.post("/scores")
@login_required
def score_create():
    db = SessionLocal()
    try:
        team_id = uuid.UUID(request.form["team_id"])
        points = int(request.form["points"])
        reason = request.form.get("reason", "").strip()
        event_date = parse_date(request.form.get("event_date")) or today_local()

        if not db.get(Team, team_id):
            abort(404)

        evt = ScoreEvent(
            team_id=team_id,
            points=points,
            reason=reason,
            event_date=event_date,
            created_by=current_user.login,
        )
        db.add(evt)
        db.commit()
        flash(f"Начислено {points:+d} ({reason})", "ok")
    except (ValueError, KeyError):
        flash("Некорректные данные", "error")
    finally:
        db.close()
    return redirect(request.referrer or url_for("admin.dashboard"))


@bp.get("/scores")
@login_required
def scores_list():
    db = SessionLocal()
    try:
        selected = parse_date(request.args.get("date")) or today_local()
        events = db.execute(
            select(ScoreEvent, Team)
            .join(Team, Team.id == ScoreEvent.team_id)
            .where(ScoreEvent.event_date == selected)
            .order_by(ScoreEvent.created_at.desc())
        ).all()
        teams = db.execute(
            select(Team).order_by(Team.sort_order, Team.name)
        ).scalars().all()
        return render_template(
            "admin/scores.html",
            events=events,
            selected=selected,
            today=today_local(),
            teams=teams,
        )
    finally:
        db.close()


@bp.post("/scores/<int:event_id>/delete")
@login_required
def score_delete(event_id):
    db = SessionLocal()
    try:
        evt = db.get(ScoreEvent, event_id)
        if evt:
            db.delete(evt)
            db.commit()
            flash("Удалено", "ok")
    finally:
        db.close()
    return redirect(request.referrer or url_for("admin.scores_list"))


# --- daily task ---------------------------------------------------------

@bp.route("/daily-task", methods=["GET", "POST"])
@login_required
def daily_task():
    db = SessionLocal()
    try:
        selected = parse_date(request.args.get("date") or request.form.get("event_date")) or today_local()

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            task = db.get(DailyTask, selected)
            if task:
                task.content = content
                task.updated_by = current_user.login
            else:
                task = DailyTask(
                    event_date=selected,
                    content=content,
                    updated_by=current_user.login,
                )
                db.add(task)
            db.commit()
            flash("Задание сохранено", "ok")
            return redirect(url_for("admin.daily_task", date=selected.isoformat()))

        task = db.get(DailyTask, selected)
        return render_template(
            "admin/daily_task.html",
            task=task,
            selected=selected,
            today=today_local(),
        )
    finally:
        db.close()
