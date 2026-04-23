from __future__ import annotations

import os
import platform
import uuid

import requests

import database


def _normalize_key(key: str) -> str:
    return (key or "").strip().upper()


def _device_id() -> str:
    return f"{platform.node()}-{uuid.getnode()}"


def get_client_config() -> dict:
    config = database.load_client_config()
    if os.getenv("HS_API_BASE_URL"):
        config["api_base_url"] = os.getenv("HS_API_BASE_URL", "").strip()
    if os.getenv("HS_ADMIN_TOKEN"):
        config["admin_token"] = os.getenv("HS_ADMIN_TOKEN", "").strip()
    if os.getenv("HS_ADMIN_CODE"):
        config["admin_code"] = os.getenv("HS_ADMIN_CODE", "").strip()
    return config


def save_client_config(api_base_url: str, admin_token: str | None = None, admin_code: str | None = None) -> None:
    current = database.load_client_config()
    current["api_base_url"] = (api_base_url or "").strip().rstrip("/")
    if admin_token is not None:
        current["admin_token"] = admin_token.strip()
    if admin_code is not None:
        current["admin_code"] = admin_code.strip()
    database.save_client_config(current)


def _api_base_url() -> str:
    return get_client_config().get("api_base_url", "").strip().rstrip("/")


def _admin_code() -> str:
    return get_client_config().get("admin_code", "").strip().upper()


def _admin_headers() -> dict:
    token = get_client_config().get("admin_token", "").strip()
    return {"X-Admin-Token": token} if token else {}


def _request(method: str, path: str, *, json_payload: dict | None = None, admin: bool = False) -> requests.Response:
    base_url = _api_base_url()
    if not base_url:
        raise RuntimeError("서버 주소가 설정되지 않았습니다.")

    headers = _admin_headers() if admin else {}
    response = requests.request(
        method=method,
        url=f"{base_url}{path}",
        json=json_payload,
        headers=headers,
        timeout=10,
    )
    return response


def _extract_error(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return str(data.get("detail") or data.get("message") or "서버 요청에 실패했습니다.")
    except ValueError:
        pass
    return response.text.strip() or "서버 요청에 실패했습니다."


def login(key: str, auto_login: bool = False) -> dict:
    normalized = _normalize_key(key)
    if normalized == _admin_code():
        _save_session(normalized, "admin", auto_login)
        return {"ok": True, "type": "admin", "key": normalized}

    try:
        response = _request(
            "POST",
            "/auth/login",
            json_payload={"key": normalized, "device_id": _device_id()},
        )
    except requests.RequestException:
        return {"ok": False, "error": "라이선스 서버에 연결할 수 없습니다."}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    if not response.ok:
        return {"ok": False, "error": _extract_error(response)}

    info = response.json()
    db = database.load_db()
    database.ensure_profile_capacity(
        db,
        int(info.get("message_limit", 1) or 1),
        int(info.get("webhook_limit", 1) or 1),
    )
    db["profile"]["last_license_key"] = normalized
    database.save_all(db)
    _save_session(normalized, "user", auto_login)
    return {"ok": True, **info}


def try_auto_login() -> dict | None:
    session = database.load_session()
    if not session.get("auto_login") or not session.get("key"):
        return None

    if session.get("type") == "admin":
        if session.get("key") == _admin_code():
            return {"ok": True, "type": "admin", "key": session["key"]}
        database.clear_session()
        return None

    info = refresh_user_info(session["key"])
    if info:
        return {"ok": True, **info}

    database.clear_session()
    return None


def refresh_user_info(license_key: str) -> dict | None:
    try:
        response = _request(
            "POST",
            "/auth/validate",
            json_payload={"key": _normalize_key(license_key), "device_id": _device_id()},
        )
    except (requests.RequestException, RuntimeError):
        return None

    if not response.ok:
        return None
    return response.json()


def create_license(days: int, message_limit: int, webhook_limit: int) -> dict:
    try:
        response = _request(
            "POST",
            "/admin/licenses",
            json_payload={
                "days": max(1, int(days)),
                "message_limit": max(1, int(message_limit)),
                "webhook_limit": max(1, int(webhook_limit)),
            },
            admin=True,
        )
    except requests.RequestException:
        return {"ok": False, "error": "라이선스 서버에 연결할 수 없습니다."}
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    if not response.ok:
        return {"ok": False, "error": _extract_error(response)}
    return {"ok": True, **response.json()}


def get_license_overview(state: str | None = None) -> list[dict]:
    try:
        suffix = f"?status={state}" if state else ""
        response = _request("GET", f"/admin/licenses{suffix}", admin=True)
    except (requests.RequestException, RuntimeError):
        return []

    if not response.ok:
        return []
    data = response.json()
    return data if isinstance(data, list) else []


def delete_license(key: str) -> bool:
    try:
        response = _request("DELETE", f"/admin/licenses/{_normalize_key(key)}", admin=True)
    except (requests.RequestException, RuntimeError):
        return False
    return response.ok


def delete_licenses_by_state(state: str) -> int:
    try:
        response = _request("DELETE", f"/admin/licenses/status/{state}", admin=True)
    except (requests.RequestException, RuntimeError):
        return 0
    if not response.ok:
        return 0
    try:
        return int(response.json().get("deleted_count", 0))
    except (ValueError, AttributeError):
        return 0


def get_last_license_key() -> str:
    db = database.load_db()
    return db.get("profile", {}).get("last_license_key", "")


def logout() -> None:
    database.clear_session()


def _save_session(key: str, user_type: str, auto_login: bool) -> None:
    if auto_login:
        database.save_session(
            {
                "auto_login": True,
                "key": key,
                "type": user_type,
            }
        )
    else:
        database.clear_session()
