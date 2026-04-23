from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"
SESSION_PATH = DATA_DIR / "session.dat"
CLIENT_CONFIG_PATH = DATA_DIR / "client_config.json"

SCHEMA_VERSION = 2


def _default_slot(index: int) -> dict:
    return {
        "title": f"메시지 {index + 1}",
        "content": "",
        "interval_days": 1,
        "webhooks": [""],
        "last_sent_at": None,
        "sending_enabled": False,
        "next_attempt_at": None,
        "last_result": None,
        "last_error": "",
    }


def _default_profile() -> dict:
    return {
        "slots": [_default_slot(0)],
        "last_license_key": "",
    }


def _default_db() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "licenses": {},
        "profile": _default_profile(),
    }


def _default_session() -> dict:
    return {
        "auto_login": False,
        "key": "",
        "type": "",
    }


def _default_client_config() -> dict:
    return {
        "api_base_url": "http://127.0.0.1:8000",
        "admin_token": "",
        "admin_code": "HSYBVC",
    }


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_PATH.exists():
        save_all(_default_db())
    else:
        save_all(_migrate_data(_read_json(CONFIG_PATH, _default_db())))

    if not SESSION_PATH.exists():
        save_session(_default_session())
    else:
        save_session(_read_json(SESSION_PATH, _default_session()))

    if not CLIENT_CONFIG_PATH.exists():
        save_client_config(_default_client_config())
    else:
        save_client_config(_read_json(CLIENT_CONFIG_PATH, _default_client_config()))


def _read_json(path: Path, fallback: dict) -> dict:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return deepcopy(fallback)
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return deepcopy(fallback)


def _migrate_data(raw: dict) -> dict:
    if raw.get("schema_version") == SCHEMA_VERSION and "profile" in raw and "licenses" in raw:
        migrated = deepcopy(raw)
    elif "messages" in raw or "webhooks" in raw:
        messages = raw.get("messages", [])
        webhooks = raw.get("webhooks", [])
        slot_count = max(len(messages), len(webhooks), 1)
        slots = []
        for index in range(slot_count):
            slot = _default_slot(index)
            slot["content"] = messages[index] if index < len(messages) else ""
            slot["webhooks"] = [webhooks[index]] if index < len(webhooks) else [""]
            slots.append(slot)
        migrated = {
            "schema_version": SCHEMA_VERSION,
            "licenses": {},
            "profile": {
                "slots": slots,
                "last_license_key": raw.get("last_license", ""),
            },
        }
    elif "slots" in raw:
        slots = []
        for index, legacy_slot in enumerate(raw.get("slots", [])):
            slot = _default_slot(index)
            slot["content"] = legacy_slot.get("msg", "")
            slot["webhooks"] = list(legacy_slot.get("urls", [""])) or [""]
            slots.append(slot)
        migrated = {
            "schema_version": SCHEMA_VERSION,
            "licenses": {},
            "profile": {
                "slots": slots or [_default_slot(0)],
                "last_license_key": raw.get("last_license", ""),
            },
        }
    else:
        migrated = _default_db()

    migrated["schema_version"] = SCHEMA_VERSION
    migrated.setdefault("licenses", {})
    migrated.setdefault("profile", _default_profile())
    migrated["profile"].setdefault("last_license_key", "")
    migrated["profile"]["slots"] = _normalize_slots(migrated["profile"].get("slots", []))
    return migrated


def _normalize_slots(slots: list) -> list:
    normalized = []
    for index, raw_slot in enumerate(slots):
        slot = _default_slot(index)
        slot["title"] = (raw_slot.get("title") or f"메시지 {index + 1}").strip() or f"메시지 {index + 1}"
        slot["content"] = raw_slot.get("content", raw_slot.get("msg", ""))
        slot["interval_days"] = max(1, int(raw_slot.get("interval_days", 1) or 1))
        slot["webhooks"] = list(raw_slot.get("webhooks", raw_slot.get("urls", [""]))) or [""]
        slot["last_sent_at"] = raw_slot.get("last_sent_at")
        slot["sending_enabled"] = bool(raw_slot.get("sending_enabled", False))
        slot["next_attempt_at"] = raw_slot.get("next_attempt_at")
        slot["last_result"] = raw_slot.get("last_result")
        slot["last_error"] = raw_slot.get("last_error", "")
        normalized.append(slot)

    return normalized or [_default_slot(0)]


def load_db() -> dict:
    return _migrate_data(_read_json(CONFIG_PATH, _default_db()))


def save_all(data: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(_migrate_data(data), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_session() -> dict:
    return _read_json(SESSION_PATH, _default_session())


def save_session(data: dict) -> None:
    session = _default_session()
    session.update(data or {})
    SESSION_PATH.write_text(
        json.dumps(session, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_session() -> None:
    save_session(_default_session())


def load_client_config() -> dict:
    config = _default_client_config()
    config.update(_read_json(CLIENT_CONFIG_PATH, _default_client_config()))
    return config


def save_client_config(data: dict) -> None:
    config = _default_client_config()
    config.update(data or {})
    CLIENT_CONFIG_PATH.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def ensure_profile_capacity(db: dict, slot_count: int, webhook_count: int) -> dict:
    profile = db.setdefault("profile", _default_profile())
    slots = profile.setdefault("slots", [_default_slot(0)])

    while len(slots) < max(1, slot_count):
        slots.append(_default_slot(len(slots)))

    for index, slot in enumerate(slots):
        slot["title"] = (slot.get("title") or f"메시지 {index + 1}").strip() or f"메시지 {index + 1}"
        slot["interval_days"] = max(1, int(slot.get("interval_days", 1) or 1))
        slot.setdefault("content", "")
        slot.setdefault("last_sent_at", None)
        slot.setdefault("sending_enabled", False)
        slot.setdefault("next_attempt_at", None)
        slot.setdefault("last_result", None)
        slot.setdefault("last_error", "")
        slot_webhooks = list(slot.get("webhooks", [""])) or [""]
        while len(slot_webhooks) < max(1, webhook_count):
            slot_webhooks.append("")
        slot["webhooks"] = slot_webhooks

    return db
