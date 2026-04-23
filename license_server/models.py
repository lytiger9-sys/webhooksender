from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class License(SQLModel, table=True):
    key: str = Field(primary_key=True, index=True, max_length=10)
    days: int
    message_limit: int
    webhook_limit: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    device_id: Optional[str] = Field(default=None, max_length=255)


class LicenseCreateRequest(SQLModel):
    days: int
    message_limit: int
    webhook_limit: int


class LoginRequest(SQLModel):
    key: str
    device_id: Optional[str] = None


class ValidateRequest(SQLModel):
    key: str
    device_id: Optional[str] = None


class LicenseResponse(SQLModel):
    ok: bool = True
    type: str = "user"
    license_key: str
    days: int
    message_limit: int
    webhook_limit: int
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remaining_seconds: int
    remaining_text: str


class LicenseItem(SQLModel):
    key: str
    status: str
    days: int
    message_limit: int
    webhook_limit: int
    created_at: datetime
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remaining_text: str
