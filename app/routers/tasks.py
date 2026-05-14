from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Room, Task, TaskCompletion, User
from app.schemas import TaskOut
from app.services.scheduling import is_due, overdue_days

router = APIRouter()


def _latest_completion_map(db: Session) -> dict[int, TaskCompletion]:
    sub = (
        db.query(
            TaskCompletion.task_id,
            func.max(TaskCompletion.completed_at).label("max_at"),
        )
        .group_by(TaskCompletion.task_id)
        .subquery()
    )
    rows = (
        db.query(TaskCompletion, User.username)
        .join(sub, (TaskCompletion.task_id == sub.c.task_id) & (TaskCompletion.completed_at == sub.c.max_at))
        .join(User, User.id == TaskCompletion.user_id)
        .all()
    )
    return {tc.task_id: (tc, username) for tc, username in rows}


def _serialize(task: Task, room: Room, completion_info) -> TaskOut:
    last_at = None
    last_by = None
    if completion_info:
        tc, username = completion_info
        last_at = tc.completed_at
        last_by = username
    return TaskOut(
        id=task.id,
        room_id=room.id,
        room=room.name,
        floor=room.floor,
        icon=room.icon,
        name=task.name,
        frequency=task.frequency,
        minutes=task.minutes,
        calories=task.calories,
        hint=task.hint,
        last_completed_at=last_at,
        last_completed_by=last_by,
        overdue_days=overdue_days(last_at, task.frequency),
    )


@router.get("/due", response_model=list[TaskOut])
def list_due(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = (
        db.query(Task, Room)
        .join(Room, Task.room_id == Room.id)
        .filter(Task.is_active.is_(True), Room.is_active.is_(True))
        .order_by(Room.order_index, Task.name)
        .all()
    )
    latest = _latest_completion_map(db)
    out: list[TaskOut] = []
    for task, room in tasks:
        info = latest.get(task.id)
        last_at = info[0].completed_at if info else None
        if is_due(last_at, task.frequency):
            out.append(_serialize(task, room, info))
    out.sort(key=lambda t: (-t.overdue_days, t.floor, t.room, t.name))
    return out


@router.get("/all", response_model=list[TaskOut])
def list_all(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tasks = (
        db.query(Task, Room)
        .join(Room, Task.room_id == Room.id)
        .filter(Task.is_active.is_(True), Room.is_active.is_(True))
        .order_by(Room.order_index, Task.name)
        .all()
    )
    latest = _latest_completion_map(db)
    return [_serialize(task, room, latest.get(task.id)) for task, room in tasks]


@router.post("/{task_id}/complete", response_model=TaskOut)
def complete(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = (
        db.query(Task, Room)
        .join(Room, Task.room_id == Room.id)
        .filter(Task.id == task_id, Task.is_active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task nicht gefunden")
    task, room = row
    tc = TaskCompletion(
        task_id=task.id,
        user_id=user.id,
        completed_at=datetime.utcnow(),
        minutes=task.minutes,
        calories=task.calories,
    )
    db.add(tc)
    db.commit()
    return _serialize(task, room, (tc, user.username))
