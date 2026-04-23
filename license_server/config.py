from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = BASE_DIR / "data"


def get_database_url() -> str:
    return os.getenv("HS_LICENSE_DATABASE_URL", f"sqlite:///{(DEFAULT_DATA_DIR / 'licenses.db').as_posix()}")


def get_admin_token() -> str:
    return os.getenv("HS_ADMIN_TOKEN", "CHANGE-ME-ADMIN-TOKEN")


def get_api_host() -> str:
    return os.getenv("HS_LICENSE_HOST", "0.0.0.0")


def get_api_port() -> int:
    return int(os.getenv("HS_LICENSE_PORT", "8000"))
