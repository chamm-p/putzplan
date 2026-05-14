from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Room, User
from app.schemas import RoomOut

router = APIRouter()


@router.get("", response_model=list[RoomOut])
def list_rooms(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Room)
        .filter(Room.is_active.is_(True))
        .order_by(Room.order_index)
        .all()
    )
