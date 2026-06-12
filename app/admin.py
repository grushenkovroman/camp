import uuid
from datetime import date, datetime, time, timedelta
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
from sqlalchemy import select, func, delete

from .db import SessionLocal
from .models import (
    Team,
    TeamMember,
    ScoreEvent,
    DailyTask,
    Shift,
    Activity,
    ScheduleBlock,
    RotationSlot,
    ScoreCategory,
)
from .auth import verify_password
from .utils import today_local, parse_date, day_index, day_label


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def _all_categories(db):
    return db.execute(
        select(ScoreCategory).order_by(ScoreCategory.sort_order, ScoreCategory.id)
    ).scalars().all()


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
            categories=_all_categories(db),
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
            categories=_all_categories(db),
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

@bp.route("/reset", methods=["GET", "POST"])
@login_required
def reset_scores():
    db = SessionLocal()
    try:
        if request.method == "POST":
            login_value = request.form.get("login", "").strip()
            password = request.form.get("password", "")
            if not verify_password(login_value, password):
                flash("Неверный логин или пароль", "error")
                return redirect(url_for("admin.reset_scores"))

            total = db.execute(
                select(func.count()).select_from(ScoreEvent)
            ).scalar_one()
            db.execute(delete(ScoreEvent))
            db.commit()
            flash(f"Сброшено: удалено {total} начислений", "ok")
            return redirect(url_for("admin.dashboard"))

        total = db.execute(
            select(func.count()).select_from(ScoreEvent)
        ).scalar_one()
        return render_template("admin/reset.html", total=total)
    finally:
        db.close()


@bp.route("/daily-task", methods=["GET", "POST"])
@login_required
def daily_task():
    db = SessionLocal()
    try:
        selected = parse_date(request.args.get("date") or request.form.get("event_date")) or today_local()

        if request.method == "POST":
            content = request.form.get("content", "").strip()
            feature = request.form.get("feature", "").strip()
            task = db.get(DailyTask, selected)
            if task:
                task.content = content
                task.feature = feature
                task.updated_by = current_user.login
            else:
                task = DailyTask(
                    event_date=selected,
                    content=content,
                    feature=feature,
                    updated_by=current_user.login,
                )
                db.add(task)
            db.commit()
            flash("Сохранено", "ok")
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


# === checkup ===========================================================

@bp.route("/checkup", methods=["GET", "POST"])
@login_required
def checkup_times():
    db = SessionLocal()
    try:
        teams = db.execute(
            select(Team).order_by(Team.sort_order, Team.name)
        ).scalars().all()

        if request.method == "POST":
            for t in teams:
                raw = request.form.get(f"checkup_{t.id}", "").strip()
                t.checkup_time = _parse_time(raw) if raw else None
            db.commit()
            flash("Времена чек-апа сохранены", "ok")
            return redirect(url_for("admin.checkup_times"))

        return render_template("admin/checkup.html", teams=teams)
    finally:
        db.close()


# === smena =============================================================

@bp.route("/shift", methods=["GET", "POST"])
@login_required
def shift_settings():
    db = SessionLocal()
    try:
        shift = db.get(Shift, 1)
        if request.method == "POST":
            start = parse_date(request.form.get("start_date"))
            total = int(request.form.get("total_days") or 8)
            name = request.form.get("name", "").strip()
            if not start or total < 2:
                flash("Некорректные данные", "error")
                return redirect(url_for("admin.shift_settings"))
            if shift:
                shift.start_date = start
                shift.total_days = total
                shift.name = name
            else:
                shift = Shift(id=1, start_date=start, total_days=total, name=name)
                db.add(shift)
            db.commit()
            flash("Смена сохранена", "ok")
            return redirect(url_for("admin.shift_settings"))

        days_preview = []
        if shift:
            for i in range(shift.total_days):
                d = shift.start_date + timedelta(days=i)
                if i == 0:
                    label = "День заезда"
                elif i == shift.total_days - 1:
                    label = "День выезда"
                else:
                    label = f"День {i}"
                days_preview.append((i, d, label))
        return render_template("admin/shift.html", shift=shift, days_preview=days_preview)
    finally:
        db.close()


# === activities ========================================================

@bp.get("/activities")
@login_required
def activities_list():
    db = SessionLocal()
    try:
        items = db.execute(
            select(Activity).order_by(Activity.sort_order, Activity.name)
        ).scalars().all()
        return render_template("admin/activities.html", items=items)
    finally:
        db.close()


@bp.post("/activities")
@login_required
def activity_create():
    db = SessionLocal()
    try:
        name = request.form.get("name", "").strip()
        if not name:
            flash("Введите название", "error")
            return redirect(url_for("admin.activities_list"))
        max_sort = db.execute(
            select(func.coalesce(func.max(Activity.sort_order), 0))
        ).scalar_one()
        db.add(Activity(
            name=name,
            description=request.form.get("description", "").strip(),
            place=request.form.get("place", "").strip(),
            icon=request.form.get("icon", "").strip()[:8],
            sort_order=max_sort + 1,
        ))
        db.commit()
        flash("Активность добавлена", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.activities_list"))


@bp.post("/activities/<int:item_id>")
@login_required
def activity_update(item_id):
    db = SessionLocal()
    try:
        a = db.get(Activity, item_id)
        if not a:
            abort(404)
        a.name = request.form.get("name", a.name).strip() or a.name
        a.description = request.form.get("description", "").strip()
        a.place = request.form.get("place", "").strip()
        a.icon = request.form.get("icon", "").strip()[:8]
        db.commit()
        flash("Сохранено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.activities_list"))


@bp.post("/activities/<int:item_id>/delete")
@login_required
def activity_delete(item_id):
    db = SessionLocal()
    try:
        a = db.get(Activity, item_id)
        if a:
            db.delete(a)
            db.commit()
            flash("Удалено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.activities_list"))


# === score categories ==================================================

def _category_kind(raw: str | None, fallback: str = "bonus") -> str:
    return raw if raw in ("bonus", "penalty", "mixed") else fallback


@bp.get("/categories")
@login_required
def categories_list():
    db = SessionLocal()
    try:
        return render_template("admin/categories.html", items=_all_categories(db))
    finally:
        db.close()


@bp.post("/categories")
@login_required
def category_create():
    db = SessionLocal()
    try:
        name = request.form.get("name", "").strip()
        if not name:
            flash("Введите название", "error")
            return redirect(url_for("admin.categories_list"))
        try:
            default_points = int(request.form.get("default_points") or 0)
        except ValueError:
            default_points = 0
        max_sort = db.execute(
            select(func.coalesce(func.max(ScoreCategory.sort_order), 0))
        ).scalar_one()
        db.add(ScoreCategory(
            name=name,
            points_label=request.form.get("points_label", "").strip(),
            default_points=default_points,
            kind=_category_kind(request.form.get("kind")),
            sort_order=max_sort + 1,
        ))
        db.commit()
        flash("Категория добавлена", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.categories_list"))


@bp.post("/categories/<int:item_id>")
@login_required
def category_update(item_id):
    db = SessionLocal()
    try:
        c = db.get(ScoreCategory, item_id)
        if not c:
            abort(404)
        c.name = request.form.get("name", c.name).strip() or c.name
        c.points_label = request.form.get("points_label", "").strip()
        try:
            c.default_points = int(request.form.get("default_points") or c.default_points)
        except ValueError:
            pass
        c.kind = _category_kind(request.form.get("kind"), c.kind)
        try:
            c.sort_order = int(request.form.get("sort_order") or c.sort_order)
        except ValueError:
            pass
        db.commit()
        flash("Сохранено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.categories_list"))


@bp.post("/categories/<int:item_id>/delete")
@login_required
def category_delete(item_id):
    db = SessionLocal()
    try:
        c = db.get(ScoreCategory, item_id)
        if c:
            db.delete(c)
            db.commit()
            flash("Удалено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.categories_list"))


# === schedule blocks ===================================================

@bp.get("/schedule")
@login_required
def schedule_list():
    db = SessionLocal()
    try:
        items = db.execute(
            select(ScheduleBlock).order_by(ScheduleBlock.block_time, ScheduleBlock.sort_order)
        ).scalars().all()
        shift = db.get(Shift, 1)
        teams = db.execute(select(Team).order_by(Team.sort_order)).scalars().all()
        return render_template(
            "admin/schedule.html",
            items=items,
            shift=shift,
            teams=teams,
            day_count=(shift.total_days if shift else 8),
        )
    finally:
        db.close()


def _form_active_days() -> list[int]:
    raw = request.form.getlist("active_days")
    days = []
    for v in raw:
        try:
            days.append(int(v))
        except ValueError:
            pass
    return sorted(set(days))


@bp.post("/schedule")
@login_required
def schedule_create():
    db = SessionLocal()
    try:
        t = _parse_time(request.form.get("block_time"))
        title = request.form.get("title", "").strip()
        if not t or not title:
            flash("Нужно указать время и название", "error")
            return redirect(url_for("admin.schedule_list"))
        kind = request.form.get("kind", "fixed")
        if kind not in ("fixed", "rotation"):
            kind = "fixed"
        rot_slot = request.form.get("rotation_slot")
        try:
            rot_slot = int(rot_slot) if rot_slot not in (None, "") else None
        except ValueError:
            rot_slot = None
        if kind != "rotation":
            rot_slot = None
        only_team = request.form.get("only_for_team_id") or None
        only_team_uuid = uuid.UUID(only_team) if only_team else None

        max_sort = db.execute(
            select(func.coalesce(func.max(ScheduleBlock.sort_order), 0))
        ).scalar_one()
        db.add(ScheduleBlock(
            sort_order=max_sort + 1,
            block_time=t,
            icon=request.form.get("icon", "").strip()[:8],
            title=title,
            description=request.form.get("description", "").strip(),
            active_days=_form_active_days(),
            kind=kind,
            rotation_slot=rot_slot,
            only_for_team_id=only_team_uuid,
        ))
        db.commit()
        flash("Блок добавлен", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.schedule_list"))


@bp.post("/schedule/<int:item_id>")
@login_required
def schedule_update(item_id):
    db = SessionLocal()
    try:
        b = db.get(ScheduleBlock, item_id)
        if not b:
            abort(404)
        t = _parse_time(request.form.get("block_time"))
        if t:
            b.block_time = t
        b.icon = request.form.get("icon", "").strip()[:8]
        b.title = request.form.get("title", b.title).strip() or b.title
        b.description = request.form.get("description", "").strip()
        b.active_days = _form_active_days()
        kind = request.form.get("kind", b.kind)
        if kind in ("fixed", "rotation"):
            b.kind = kind
        rot_slot = request.form.get("rotation_slot")
        try:
            b.rotation_slot = int(rot_slot) if rot_slot not in (None, "") else None
        except ValueError:
            b.rotation_slot = None
        if b.kind != "rotation":
            b.rotation_slot = None
        only_team = request.form.get("only_for_team_id") or None
        b.only_for_team_id = uuid.UUID(only_team) if only_team else None
        db.commit()
        flash("Сохранено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.schedule_list"))


@bp.post("/schedule/<int:item_id>/delete")
@login_required
def schedule_delete(item_id):
    db = SessionLocal()
    try:
        b = db.get(ScheduleBlock, item_id)
        if b:
            db.delete(b)
            db.commit()
            flash("Удалено", "ok")
    finally:
        db.close()
    return redirect(url_for("admin.schedule_list"))


# === rotation grid =====================================================

@bp.route("/rotation", methods=["GET", "POST"])
@login_required
def rotation_grid():
    db = SessionLocal()
    try:
        shift = db.get(Shift, 1)
        total_days = shift.total_days if shift else 8
        try:
            day = int(request.args.get("day", 1))
        except ValueError:
            day = 1
        day = max(0, min(day, total_days - 1))

        teams = db.execute(
            select(Team).where(Team.in_rotation == True)
            .order_by(Team.sort_order)
        ).scalars().all()
        activities = db.execute(
            select(Activity).order_by(Activity.sort_order, Activity.name)
        ).scalars().all()

        if request.method == "POST":
            try:
                post_day = int(request.form.get("day_index"))
            except (TypeError, ValueError):
                flash("Некорректный day_index", "error")
                return redirect(url_for("admin.rotation_grid", day=day))

            # удаляем существующие записи на этот день и пишем новые
            db.execute(
                delete(RotationSlot).where(RotationSlot.day_index == post_day)
            )
            for t in teams:
                for slot in range(3):
                    val = request.form.get(f"slot_{t.id}_{slot}")
                    if val:
                        try:
                            aid = int(val)
                        except ValueError:
                            continue
                        db.add(RotationSlot(
                            team_id=t.id,
                            day_index=post_day,
                            slot_position=slot,
                            activity_id=aid,
                        ))
            db.commit()
            flash(f"Ротация на день {post_day} сохранена", "ok")
            return redirect(url_for("admin.rotation_grid", day=post_day))

        # GET — собрать матрицу для отображения
        rows = db.execute(
            select(RotationSlot).where(RotationSlot.day_index == day)
        ).scalars().all()
        current = {(r.team_id, r.slot_position): r.activity_id for r in rows}

        slot_times = ["10:00", "11:00", "12:00"]
        label = None
        if shift:
            label = day_label(shift, shift.start_date + timedelta(days=day))

        return render_template(
            "admin/rotation.html",
            shift=shift,
            day=day,
            total_days=total_days,
            day_label_text=label,
            teams=teams,
            activities=activities,
            current=current,
            slot_times=slot_times,
        )
    finally:
        db.close()
