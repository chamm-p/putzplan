from datetime import datetime, timedelta

FREQ_DAYS = {"weekly": 7, "monthly": 30, "yearly": 365}


def days_for(freq: str) -> int:
    return FREQ_DAYS.get(freq, 7)


def is_due(last_completed_at: datetime | None, freq: str, now: datetime | None = None) -> bool:
    if last_completed_at is None:
        return True
    now = now or datetime.utcnow()
    return now >= last_completed_at + timedelta(days=days_for(freq))


def overdue_days(last_completed_at: datetime | None, freq: str, now: datetime | None = None) -> float:
    if last_completed_at is None:
        return 9999.0
    now = now or datetime.utcnow()
    due_at = last_completed_at + timedelta(days=days_for(freq))
    if now < due_at:
        return 0.0
    return round((now - due_at).total_seconds() / 86400.0, 2)
