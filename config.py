import os
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ── Bot credentials ──────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")

# ── Access control ───────────────────────────────────────────────────────────
# Comma-separated role names that are allowed to use bot commands.
BOT_ALLOWED_ROLES: List[str] = [
    r.strip()
    for r in os.getenv("BOT_ALLOWED_ROLES", "Administrator,Moderator").split(",")
    if r.strip()
]

# ── Optional webhook for structured logs ─────────────────────────────────────
LOG_WEBHOOK_URL: str = os.getenv("LOG_WEBHOOK_URL", "")

# ── Rate limiting ─────────────────────────────────────────────────────────────
try:
    RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "10"))
except ValueError:
    RATE_LIMIT_SECONDS = 10


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
