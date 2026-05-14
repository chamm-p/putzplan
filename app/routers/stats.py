from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import TaskCompletion, User
from app.schemas import LeaderboardEntry, TodayStats

router = APIRouter()


def _start_of_today_utc() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, now.day)


@router.get("/today", response_model=TodayStats)
def today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = _start_of_today_utc()
    row = (
        db.query(
            func.count(TaskCompletion.id),
            func.coalesce(func.sum(TaskCompletion.minutes), 0),
            func.coalesce(func.sum(TaskCompletion.calories), 0),
        )
        .filter(TaskCompletion.user_id == user.id, TaskCompletion.completed_at >= since)
        .one()
    )
    return TodayStats(completions=row[0] or 0, minutes=int(row[1] or 0), calories=int(row[2] or 0))


@router.get("/leaderboard/today", response_model=list[LeaderboardEntry])
def leaderboard_today(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = _start_of_today_utc()
    return _leaderboard(db, user, since)


@router.get("/leaderboard/putzkoenig", response_model=list[LeaderboardEntry])
def leaderboard_putzkoenig(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=settings.LEADERBOARD_DAYS)
    return _leaderboard(db, user, since)


def _leaderboard(db: Session, current: User, since: datetime) -> list[LeaderboardEntry]:
    rows = (
        db.query(
            User.username,
            User.id,
            func.count(TaskCompletion.id),
            func.coalesce(func.sum(TaskCompletion.minutes), 0),
            func.coalesce(func.sum(TaskCompletion.calories), 0),
        )
        .join(TaskCompletion, TaskCompletion.user_id == User.id)
        .filter(TaskCompletion.completed_at >= since)
        .group_by(User.id, User.username)
        .order_by(func.sum(TaskCompletion.calories).desc())
        .all()
    )
    return [
        LeaderboardEntry(
            username=username,
            completions=count,
            minutes=int(minutes or 0),
            calories=int(calories or 0),
            is_self=(uid == current.id),
        )
        for username, uid, count, minutes, calories in rows
    ]
