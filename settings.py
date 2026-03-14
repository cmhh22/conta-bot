"""
Centralized settings loader for secrets and admin configuration.
- Reads from environment variables by default.
- Optionally overrides from local config_secret.py if present.

Environment variables:
- TELEGRAM_BOT_TOKEN: Telegram bot token
- ADMIN_USER_IDS: Comma-separated list of Telegram user IDs allowed as admins (e.g., "12345,67890")
"""
from __future__ import annotations
import os
from typing import List

# Defaults from environment
_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_admin_ids_env = os.getenv("ADMIN_USER_IDS", "")
_ADMIN_USER_IDS: List[int] = []
if _admin_ids_env.strip():
    try:
        _ADMIN_USER_IDS = [int(x.strip()) for x in _admin_ids_env.split(",") if x.strip()]
    except ValueError:
        # If parsing fails, leave empty to avoid accidental grants
        _ADMIN_USER_IDS = []

# Optional local override via config_secret.py
try:
    from config_secret import TOKEN as _TOKEN_LOCAL, ADMIN_USER_IDS as _ADMIN_USER_IDS_LOCAL  # type: ignore
    TOKEN: str = _TOKEN_LOCAL or _TOKEN
    ADMIN_USER_IDS: List[int] = _ADMIN_USER_IDS_LOCAL or _ADMIN_USER_IDS
except Exception:
    TOKEN = _TOKEN
    ADMIN_USER_IDS = _ADMIN_USER_IDS

# Ensure types and safe fallbacks
if not isinstance(ADMIN_USER_IDS, list):
    ADMIN_USER_IDS = []
