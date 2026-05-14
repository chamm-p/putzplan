from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    username: str
    email: str


class RoomOut(BaseModel):
    id: int
    floor: str
    name: str
    icon: str
    slug: str

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: int
    room_id: int
    room: str
    floor: str
    icon: str
    name: str
    frequency: str
    minutes: int
    calories: int
    hint: str
    last_completed_at: Optional[datetime] = None
    last_completed_by: Optional[str] = None
    overdue_days: float = 0.0


class ChatRequest(BaseModel):
    text: str


class ChatResponse(BaseModel):
    answer: str
    transcript: Optional[str] = None


class LeaderboardEntry(BaseModel):
    username: str
    completions: int
    minutes: int
    calories: int
    is_self: bool = False


class TodayStats(BaseModel):
    completions: int
    minutes: int
    calories: int
