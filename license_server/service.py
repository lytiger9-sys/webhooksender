from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from license_server.models import License, LicenseItem, LicenseResponse


LICENSE_PREFIX = "HS"
LICENSE_TOKEN_SIZE = 8


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_key(key: str) -> str:
    return (key or "").strip().upper()


def normalize_device_id(device_id: str | None) -> str | None:
    clean = (device_id or "").strip()
    return clean or None


def create_license(session: Session, days: int, message_limit: int, webhook_limit: int) -> License:
    license_obj = License(
        key=generate_unique_key(session),
        days=max(1, int(days)),
        message_limit=max(1, int(message_limit)),
        webhook_limit=max(1, int(webhook_limit)),
    )
    session.add(license_obj)
    session.commit()
    session.refresh(license_obj)
    return license_obj


def generate_unique_key(session: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        token = "".join(secrets.choice(alphabet) for _ in range(LICENSE_TOKEN_SIZE))
        key = f"{LICENSE_PREFIX}{token}"
        if not session.get(License, key):
            return key


def get_status(license_obj: License) -> str:
    if not license_obj.activated_at or not license_obj.expires_at:
        return "unused"
    if license_obj.expires_at <= utc_now():
        return "expired"
    return "active"


def format_remaining(expires_at: datetime | None) -> tuple[int, str]:
    if not expires_at:
        return 0, "만료됨"

    total_seconds = max(0, int((expires_at - utc_now()).total_seconds()))
    if total_seconds <= 0:
        return 0, "만료됨"

    days = total_seconds // 86400
    if days >= 1:
        return total_seconds, f"{days}일"

    hours = total_seconds // 3600
    minutes = max(0, (total_seconds % 3600) // 60)
    return total_seconds, f"{hours}시간 {minutes}분"


def serialize_license(license_obj: License) -> LicenseResponse:
    remaining_seconds, remaining_text = format_remaining(license_obj.expires_at)
    return LicenseResponse(
        license_key=license_obj.key,
        days=license_obj.days,
        message_limit=license_obj.message_limit,
        webhook_limit=license_obj.webhook_limit,
        activated_at=license_obj.activated_at,
        expires_at=license_obj.expires_at,
        remaining_seconds=remaining_seconds,
        remaining_text=remaining_text,
    )


def serialize_license_item(license_obj: License) -> LicenseItem:
    _, remaining_text = format_remaining(license_obj.expires_at)
    return LicenseItem(
        key=license_obj.key,
        status=get_status(license_obj),
        days=license_obj.days,
        message_limit=license_obj.message_limit,
        webhook_limit=license_obj.webhook_limit,
        created_at=license_obj.created_at,
        activated_at=license_obj.activated_at,
        expires_at=license_obj.expires_at,
        remaining_text=remaining_text,
    )


def login_license(session: Session, key: str, device_id: str | None = None) -> LicenseResponse:
    normalized = normalize_key(key)
    if not normalized.startswith(LICENSE_PREFIX):
        raise HTTPException(status_code=400, detail="HS로 시작하는 라이선스를 입력해 주세요.")

    license_obj = session.get(License, normalized)
    if not license_obj:
        raise HTTPException(status_code=404, detail="발급된 라이선스를 찾을 수 없습니다.")

    status = get_status(license_obj)
    if status == "expired":
        raise HTTPException(status_code=403, detail="이미 만료된 라이선스입니다.")

    device_id = normalize_device_id(device_id)
    if license_obj.device_id and device_id and license_obj.device_id != device_id:
        raise HTTPException(status_code=403, detail="다른 기기에 등록된 라이선스입니다.")

    now = utc_now()
    if status == "unused":
        license_obj.activated_at = now
        license_obj.expires_at = now + timedelta(days=license_obj.days)
        if device_id:
            license_obj.device_id = device_id

    if not license_obj.device_id and device_id:
        license_obj.device_id = device_id

    license_obj.last_seen_at = now
    session.add(license_obj)
    session.commit()
    session.refresh(license_obj)
    return serialize_license(license_obj)


def validate_license(session: Session, key: str, device_id: str | None = None) -> LicenseResponse:
    normalized = normalize_key(key)
    license_obj = session.get(License, normalized)
    if not license_obj:
        raise HTTPException(status_code=404, detail="라이선스를 찾을 수 없습니다.")

    if get_status(license_obj) != "active":
        raise HTTPException(status_code=403, detail="라이선스가 활성 상태가 아닙니다.")

    device_id = normalize_device_id(device_id)
    if license_obj.device_id and device_id and license_obj.device_id != device_id:
        raise HTTPException(status_code=403, detail="등록된 기기와 일치하지 않습니다.")

    license_obj.last_seen_at = utc_now()
    session.add(license_obj)
    session.commit()
    session.refresh(license_obj)
    return serialize_license(license_obj)


def list_licenses(session: Session, status: str | None = None) -> list[LicenseItem]:
    items = session.exec(select(License)).all()
    output = []
    for license_obj in items:
        current_status = get_status(license_obj)
        if status and current_status != status:
            continue
        output.append(serialize_license_item(license_obj))
    output.sort(key=lambda item: (item.status, item.expires_at or item.created_at, item.key))
    return output


def delete_license(session: Session, key: str) -> bool:
    license_obj = session.get(License, normalize_key(key))
    if not license_obj:
        return False
    if get_status(license_obj) == "active":
        raise HTTPException(status_code=400, detail="사용중인 라이선스는 삭제할 수 없습니다.")
    session.delete(license_obj)
    session.commit()
    return True


def delete_by_status(session: Session, status: str) -> int:
    items = session.exec(select(License)).all()
    targets = [item for item in items if get_status(item) == status]
    for item in targets:
        session.delete(item)
    if targets:
        session.commit()
    return len(targets)
