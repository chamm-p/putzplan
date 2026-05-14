"""Idempotent task seeding from a YAML file.

Re-runs on every app start. Adds new rooms/tasks, updates display
fields, sets is_active=False for entries removed from the YAML
(completions stay intact).
"""
import logging
import re
import unicodedata
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Room, Task

logger = logging.getLogger(__name__)

ALLOWED_FREQ = {"weekly", "monthly", "yearly"}


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


def sync_from_yaml(path: str | None = None) -> dict:
    path = path or settings.SEED_FILE
    p = Path(path)
    if not p.exists():
        logger.warning("Seed file not found: %s", p)
        return {"loaded": False}

    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    db: Session = SessionLocal()
    try:
        yaml_room_slugs: set[str] = set()
        yaml_task_slugs: set[str] = set()
        order = 0

        for floor_block in data.get("floors", []):
            floor = floor_block.get("name", "").strip()
            if not floor:
                continue
            for room_block in floor_block.get("rooms", []):
                room_name = room_block.get("name", "").strip()
                if not room_name:
                    continue
                room_slug = f"{_slug(floor)}.{_slug(room_name)}"
                yaml_room_slugs.add(room_slug)
                icon = room_block.get("icon", "🧹")

                room = db.query(Room).filter(Room.slug == room_slug).first()
                if not room:
                    room = Room(slug=room_slug, floor=floor, name=room_name, icon=icon, order_index=order)
                    db.add(room)
                else:
                    room.floor = floor
                    room.name = room_name
                    room.icon = icon
                    room.order_index = order
                    room.is_active = True
                order += 1
                db.flush()

                for task_block in room_block.get("tasks", []):
                    name = task_block.get("name", "").strip()
                    if not name:
                        continue
                    freq = task_block.get("frequency", "weekly").lower()
                    if freq not in ALLOWED_FREQ:
                        logger.warning("Unknown frequency '%s' for task '%s' — defaulting to weekly", freq, name)
                        freq = "weekly"
                    minutes = int(task_block.get("minutes", 10))
                    calories = int(task_block.get("calories", minutes * 4))
                    hint = task_block.get("hint", "")
                    task_slug = f"{room_slug}.{_slug(name)}"
                    yaml_task_slugs.add(task_slug)

                    task = db.query(Task).filter(Task.slug == task_slug).first()
                    if not task:
                        task = Task(
                            slug=task_slug,
                            room_id=room.id,
                            name=name,
                            frequency=freq,
                            minutes=minutes,
                            calories=calories,
                            hint=hint,
                        )
                        db.add(task)
                    else:
                        task.room_id = room.id
                        task.name = name
                        task.frequency = freq
                        task.minutes = minutes
                        task.calories = calories
                        task.hint = hint
                        task.is_active = True

        # Soft-delete entries that disappeared from YAML
        for room in db.query(Room).all():
            if room.slug not in yaml_room_slugs:
                room.is_active = False
        for task in db.query(Task).all():
            if task.slug not in yaml_task_slugs:
                task.is_active = False

        db.commit()
        logger.info("Seed sync: %d rooms, %d tasks", len(yaml_room_slugs), len(yaml_task_slugs))
        return {"loaded": True, "rooms": len(yaml_room_slugs), "tasks": len(yaml_task_slugs)}
    finally:
        db.close()
