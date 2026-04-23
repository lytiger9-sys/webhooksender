from __future__ import annotations

from urllib.parse import urlparse

import requests


VALID_HOSTS = {"discord.com", "ptb.discord.com", "canary.discord.com"}


def validate_discord_webhook(webhook_url: str) -> tuple[bool, str]:
    url = (webhook_url or "").strip()
    if not url:
        return False, ""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "디스코드 웹훅이 아닙니다"

    if parsed.netloc.lower() not in VALID_HOSTS:
        return False, "디스코드 웹훅이 아닙니다"

    if not parsed.path.startswith("/api/webhooks/"):
        return False, "디스코드 웹훅이 아닙니다"

    return True, ""


def send_to_discord(webhook_url: str, content: str) -> tuple[bool, str]:
    is_valid, message = validate_discord_webhook(webhook_url)
    if not is_valid:
        return False, message or "디스코드 웹훅이 아닙니다"

    payload = {"content": content}

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in {200, 204}:
            return True, ""

        try:
            error_message = response.json().get("message", "")
        except ValueError:
            error_message = response.text.strip()

        return False, error_message or "웹훅 실행 실패"
    except requests.RequestException:
        return False, "웹훅 실행 실패"
