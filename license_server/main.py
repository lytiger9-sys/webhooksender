from __future__ import annotations

from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlmodel import Session

from license_server.config import get_admin_token, get_api_host, get_api_port
from license_server.database import get_session, init_db
from license_server.models import (
    LicenseCreateRequest,
    LicenseItem,
    LicenseResponse,
    LoginRequest,
    ValidateRequest,
)
from license_server.service import create_license, delete_by_status, delete_license, list_licenses, login_license, validate_license
from license_server.service import serialize_license_item


app = FastAPI(title="HS License Server", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if x_admin_token != get_admin_token():
        raise HTTPException(status_code=401, detail="관리자 인증에 실패했습니다.")


@app.get("/health")
def health_check() -> dict:
    return {"ok": True}


@app.post("/auth/login", response_model=LicenseResponse)
def auth_login(payload: LoginRequest, session: Session = Depends(get_session)) -> LicenseResponse:
    return login_license(session, payload.key, payload.device_id)


@app.post("/auth/validate", response_model=LicenseResponse)
def auth_validate(payload: ValidateRequest, session: Session = Depends(get_session)) -> LicenseResponse:
    return validate_license(session, payload.key, payload.device_id)


@app.post("/admin/licenses", response_model=LicenseItem, dependencies=[Depends(require_admin)])
def admin_create_license(payload: LicenseCreateRequest, session: Session = Depends(get_session)) -> LicenseItem:
    created = create_license(session, payload.days, payload.message_limit, payload.webhook_limit)
    return serialize_license_item(created)


@app.get("/admin/licenses", response_model=list[LicenseItem], dependencies=[Depends(require_admin)])
def admin_list_licenses(status: Optional[str] = None, session: Session = Depends(get_session)) -> list[LicenseItem]:
    if status and status not in {"active", "expired", "unused"}:
        raise HTTPException(status_code=400, detail="status는 active, expired, unused 중 하나여야 합니다.")
    return list_licenses(session, status)


@app.delete("/admin/licenses/{key}", dependencies=[Depends(require_admin)])
def admin_delete_license(key: str, session: Session = Depends(get_session)) -> dict:
    deleted = delete_license(session, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="라이선스를 찾을 수 없습니다.")
    return {"ok": True}


@app.delete("/admin/licenses/status/{status}", dependencies=[Depends(require_admin)])
def admin_delete_by_status(status: str, session: Session = Depends(get_session)) -> dict:
    if status not in {"expired", "unused"}:
        raise HTTPException(status_code=400, detail="expired 또는 unused만 일괄 삭제할 수 있습니다.")
    count = delete_by_status(session, status)
    return {"ok": True, "deleted_count": count}


if __name__ == "__main__":
    uvicorn.run("license_server.main:app", host=get_api_host(), port=get_api_port(), reload=False)
