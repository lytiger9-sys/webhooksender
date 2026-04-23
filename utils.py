from __future__ import annotations

from datetime import datetime, timedelta


def now_local() -> datetime:
    return datetime.now()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds")


def add_days(value: datetime, days: int) -> datetime:
    return value + timedelta(days=max(1, int(days)))


def format_timestamp(value: str | None) -> str:
    parsed = parse_iso(value)
    if not parsed:
        return ""
    return f"{parsed.month}월 {parsed.day}일 {parsed.hour:02d}시 {parsed.minute:02d}분"


def format_remaining(expires_at: str | None) -> str:
    parsed = parse_iso(expires_at)
    if not parsed:
        return "알 수 없음"

    diff = parsed - now_local()
    total_seconds = int(diff.total_seconds())
    if total_seconds <= 0:
        return "만료됨"

    days = total_seconds // 86400
    if days >= 1:
        return f"{days}일"

    hours = total_seconds // 3600
    minutes = max(0, (total_seconds % 3600) // 60)
    return f"{hours}시간 {minutes}분"


def normalize_positive_int(value: str, fallback: int = 1) -> int:
    try:
        parsed = int(value)
        return max(1, parsed)
    except (TypeError, ValueError):
        return max(1, fallback)
