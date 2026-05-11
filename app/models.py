import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    String,
    Integer,
    Text,
    Date,
    DateTime,
    Time,
    Boolean,
    ForeignKey,
    Enum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    in_rotation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
        order_by="TeamMember.sort_order",
    )
    score_events: Mapped[list["ScoreEvent"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("member", "mentor", name="member_role"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    team: Mapped[Team] = relationship(back_populates="members")


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(120))

    team: Mapped[Team] = relationship(back_populates="score_events")


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    event_date: Mapped[date] = mapped_column(Date, primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[str | None] = mapped_column(String(120))


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Shift(Base):
    __tablename__ = "shift"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="", nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    place: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    block_time: Mapped[time] = mapped_column(Time, nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active_days: Mapped[list[int]] = mapped_column(JSONB, default=list, nullable=False)
    kind: Mapped[str] = mapped_column(
        Enum("fixed", "rotation", name="block_kind"), default="fixed", nullable=False
    )
    rotation_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    only_for_team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=True,
    )


class RotationSlot(Base):
    __tablename__ = "rotation_slots"

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    day_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_position: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("activities.id", ondelete="SET NULL"), nullable=True
    )

    activity: Mapped["Activity | None"] = relationship()
