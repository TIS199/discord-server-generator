import logging
import datetime
from typing import Optional, List

try:
    import aiohttp
    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("ServerGenerator")


async def _send_webhook(payload: dict) -> None:
    if not config.LOG_WEBHOOK_URL or not _HAS_AIOHTTP:
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config.LOG_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 204:
                    logger.warning(f"Webhook log returned {resp.status}")
    except Exception as exc:
        logger.error(f"Webhook log error: {exc}")


async def log_to_webhook(
    title: str,
    description: str,
    color: int = 0x3498DB,
    fields: Optional[List[dict]] = None,
) -> None:
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "fields": fields or [],
    }
    await _send_webhook({"embeds": [embed]})


async def log_action(user: str, guild: str, action: str, details: str) -> None:
    logger.info(f"[{guild}] {user} — {action}: {details}")
    await log_to_webhook(
        title=f"✅ {action}",
        description=f"**User:** {user}\n**Guild:** {guild}",
        color=0x2ECC71,
        fields=[{"name": "Details", "value": details[:1024], "inline": False}],
    )


async def log_error(user: str, guild: str, error_type: str, message: str) -> None:
    logger.error(f"[{guild}] {user} — {error_type}: {message}")
    await log_to_webhook(
        title=f"❌ {error_type}",
        description=f"**User:** {user}\n**Guild:** {guild}",
        color=0xE74C3C,
        fields=[{"name": "Error", "value": message[:1024], "inline": False}],
    )


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
