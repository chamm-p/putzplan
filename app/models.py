from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    oidc_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    floor: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    icon: Mapped[str] = mapped_column(String(8), default="🧹")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)

    tasks: Mapped[list["Task"]] = relationship(back_populates="room", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False)  # weekly|monthly|yearly
    minutes: Mapped[int] = mapped_column(Integer, default=10)
    calories: Mapped[int] = mapped_column(Integer, default=30)
    hint: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)

    room: Mapped["Room"] = relationship(back_populates="tasks")


class TaskCompletion(Base):
    __tablename__ = "task_completions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    calories: Mapped[int] = mapped_column(Integer, default=0)
