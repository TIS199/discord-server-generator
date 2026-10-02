"""
sender.py
---------
Handles sending messages to channels and creating/using webhooks.
Called by builder.py after channels are created.
"""

import asyncio
from typing import Optional, List, Tuple

import discord
import aiohttp

from src.logger import logger


async def send_message_to_channel(
    guild: discord.Guild,
    channel_name: str,
    content: str,
) -> Tuple[bool, str]:
    """Find a text channel by name and send a message to it."""
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if channel is None:
        return False, f"Channel '{channel_name}' not found"
    try:
        # Discord message limit is 2000 chars; split if needed
        chunks = [content[i:i + 1990] for i in range(0, len(content), 1990)]
        for chunk in chunks:
            await channel.send(chunk)
            await asyncio.sleep(0.3)
        logger.info(f"  📨 Sent message to #{channel_name}")
        return True, f"Message sent to #{channel_name}"
    except discord.HTTPException as exc:
        return False, str(exc)


async def create_webhook(
    guild: discord.Guild,
    channel_name: str,
    webhook_name: str,
    avatar_url: Optional[str] = None,
) -> Tuple[bool, str, Optional[str]]:
    """
    Create a webhook in a channel.
    Returns (success, message, webhook_url).
    """
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if channel is None:
        return False, f"Channel '{channel_name}' not found", None

    try:
        avatar_bytes: Optional[bytes] = None
        if avatar_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(avatar_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 200:
                            avatar_bytes = await resp.read()
            except Exception as exc:
                logger.warning(f"Failed to fetch webhook avatar: {exc}")

        webhook = await channel.create_webhook(
            name=webhook_name,
            avatar=avatar_bytes,
            reason="Discord Server Generator blueprint",
        )
        logger.info(f"  🪝 Created webhook '{webhook_name}' in #{channel_name}")
        return True, f"Webhook '{webhook_name}' created in #{channel_name}", webhook.url
    except discord.HTTPException as exc:
        return False, str(exc), None


async def send_via_webhook(
    webhook_url: str,
    content: str,
    username: Optional[str] = None,
    avatar_url: Optional[str] = None,
) -> Tuple[bool, str]:
    """Send a message through a webhook URL."""
    payload: dict = {"content": content}
    if username:
        payload["username"] = username
    if avatar_url:
        payload["avatar_url"] = avatar_url

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status in (200, 204):
                    logger.info(f"  🪝 Sent message via webhook (username={username!r})")
                    return True, "Webhook message sent"
                else:
                    text = await resp.text()
                    return False, f"Webhook returned {resp.status}: {text[:200]}"
    except Exception as exc:
        return False, str(exc)


async def process_messages(
    guild: discord.Guild,
    messages: List[dict],
) -> List[str]:
    """
    Process the 'messages' array from the blueprint.
    Returns a list of result strings for the build report.
    """
    results: List[str] = []

    for i, msg_def in enumerate(messages):
        channel_name: str = msg_def.get("channel", "").strip()
        content: str = msg_def.get("content", "").strip()

        if not channel_name or not content:
            results.append(f"  ⚠️ message[{i}]: missing 'channel' or 'content', skipped")
            continue

        use_webhook: bool = bool(msg_def.get("use_webhook", False))
        webhook_name: str = msg_def.get("webhook_name", "ServerBot").strip() or "ServerBot"
        webhook_avatar: Optional[str] = msg_def.get("webhook_avatar_url") or None

        if use_webhook:
            # Create a fresh webhook for this send, then use it
            wh_ok, wh_msg, wh_url = await create_webhook(
                guild, channel_name, webhook_name, webhook_avatar
            )
            if not wh_ok or not wh_url:
                results.append(f"  ❌ webhook in #{channel_name}: {wh_msg}")
                continue

            send_ok, send_msg = await send_via_webhook(
                wh_url, content, username=webhook_name, avatar_url=webhook_avatar
            )
            if send_ok:
                results.append(f"  ✅ webhook-message → #{channel_name} (as '{webhook_name}')")
            else:
                results.append(f"  ❌ webhook-send to #{channel_name}: {send_msg}")
        else:
            ok, msg = await send_message_to_channel(guild, channel_name, content)
            if ok:
                results.append(f"  ✅ message → #{channel_name}")
            else:
                results.append(f"  ❌ message → #{channel_name}: {msg}")

        await asyncio.sleep(0.5)

    return results


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
