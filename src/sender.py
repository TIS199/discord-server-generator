"""Send blueprint messages with rich embeds, optional webhooks, and reactions."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import discord

from src.logger import logger


def _embed_color(value: object) -> Optional[discord.Color]:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return discord.Color(value)
    if isinstance(value, str):
        return discord.Color(int(value.lstrip("#"), 16))
    return None


def _make_embed(definition: Dict) -> discord.Embed:
    kwargs = {
        "title": definition.get("title"),
        "description": definition.get("description"),
        "url": definition.get("url"),
        "color": _embed_color(definition.get("color")),
        "timestamp": None,
    }
    if definition.get("timestamp"):
        kwargs["timestamp"] = datetime.fromisoformat(definition["timestamp"].replace("Z", "+00:00"))
    embed = discord.Embed(**kwargs)

    author = definition.get("author")
    if author:
        embed.set_author(
            name=author["name"],
            url=author.get("url"),
            icon_url=author.get("icon_url"),
        )
    footer = definition.get("footer")
    if footer:
        embed.set_footer(text=footer["text"], icon_url=footer.get("icon_url"))
    if definition.get("thumbnail_url"):
        embed.set_thumbnail(url=definition["thumbnail_url"])
    if definition.get("image_url"):
        embed.set_image(url=definition["image_url"])
    for field in definition.get("fields", []):
        embed.add_field(name=field["name"], value=field["value"], inline=field.get("inline", False))
    return embed


def _message_embeds(message: Dict) -> List[discord.Embed]:
    if "embeds" in message:
        return [_make_embed(definition) for definition in message["embeds"]]
    if "embed" in message:
        return [_make_embed(message["embed"])]
    return []


def _find_channel(
    guild: discord.Guild,
    channel_name: str,
    category_name: Optional[str] = None,
) -> Optional[discord.TextChannel]:
    """Resolve a text/news channel by name, optionally scoped to its category."""
    if "/" in channel_name and not category_name:
        category_name, channel_name = channel_name.split("/", 1)
    candidates = [channel for channel in guild.text_channels if channel.name == channel_name]
    if category_name:
        candidates = [channel for channel in candidates if channel.category and channel.category.name == category_name]
    if len(candidates) == 1:
        return candidates[0]
    return None


async def send_message_to_channel(
    guild: discord.Guild,
    channel_name: str,
    content: str,
    embeds: Optional[List[discord.Embed]] = None,
    category_name: Optional[str] = None,
    reactions: Optional[List[str]] = None,
) -> Tuple[bool, str, List[str]]:
    """Send content and embeds, then add reactions to the first sent message."""
    channel = _find_channel(guild, channel_name, category_name)
    if channel is None:
        return False, f"Text channel '{channel_name}' not found or ambiguous", []
    embeds = embeds or []
    chunks = [content[index:index + 1990] for index in range(0, len(content), 1990)] if content else [""]
    try:
        first_message: Optional[discord.Message] = None
        for index, chunk in enumerate(chunks):
            sent_message = await channel.send(
                content=chunk or None,
                embeds=embeds if index == 0 else [],
                allowed_mentions=discord.AllowedMentions.none(),
            )
            if first_message is None:
                first_message = sent_message
            await asyncio.sleep(0.3)
        reaction_errors = await _add_reactions(first_message, reactions or []) if first_message else []
        logger.info("Sent blueprint message to #%s", channel.name)
        return True, f"Message sent to #{channel.name}", reaction_errors
    except discord.HTTPException as exc:
        return False, str(exc), []


async def _add_reactions(message: discord.Message, reactions: List[str]) -> List[str]:
    """Add requested reactions to the first message and collect per-reaction failures."""
    errors: List[str] = []
    for emoji in reactions:
        try:
            await message.add_reaction(emoji)
        except Exception as exc:
            logger.warning("Could not add reaction %r to message %s: %s", emoji, message.id, exc)
            errors.append(f"{emoji!r} ({exc})")
    return errors


async def _send_via_webhook(
    channel: discord.TextChannel,
    content: str,
    embeds: List[discord.Embed],
    username: str,
    avatar_url: Optional[str],
    reactions: Optional[List[str]] = None,
) -> Tuple[bool, str, List[str]]:
    webhook: Optional[discord.Webhook] = None
    try:
        webhook = await channel.create_webhook(
            name=username,
            reason="Discord Server Generator blueprint",
        )
        chunks = [content[index:index + 1990] for index in range(0, len(content), 1990)] if content else [""]
        first_message: Optional[discord.Message] = None
        for index, chunk in enumerate(chunks):
            sent_message = await webhook.send(
                content=chunk or None,
                embeds=embeds if index == 0 else [],
                username=username,
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions.none(),
                wait=True,
            )
            if first_message is None:
                first_message = sent_message
            await asyncio.sleep(0.3)
        reaction_errors = await _add_reactions(first_message, reactions or []) if first_message else []
        return True, "Webhook message sent", reaction_errors
    except discord.HTTPException as exc:
        return False, str(exc), []
    finally:
        if webhook is not None:
            try:
                await webhook.delete(reason="One-time blueprint message webhook")
            except discord.HTTPException as exc:
                logger.warning("Could not remove one-time webhook: %s", exc)


async def process_messages(guild: discord.Guild, messages: List[dict]) -> List[str]:
    """Process message definitions and return human-readable per-message results."""
    results: List[str] = []
    for index, message_def in enumerate(messages):
        channel_name = message_def.get("channel", "").strip()
        category_name = message_def.get("category")
        content = message_def.get("content", "").strip()
        reactions = message_def.get("reactions", [])
        if not channel_name:
            results.append(f"  ❌ message[{index}]: missing channel name")
            continue

        channel = _find_channel(guild, channel_name, category_name)
        if channel is None:
            results.append(f"  ❌ message[{index}]: channel '{channel_name}' not found or ambiguous")
            continue

        try:
            embeds = _message_embeds(message_def)
            if message_def.get("use_webhook", False):
                ok, detail, reaction_errors = await _send_via_webhook(
                    channel=channel,
                    content=content,
                    embeds=embeds,
                    username=message_def.get("webhook_name", "Server Guide"),
                    avatar_url=message_def.get("webhook_avatar_url"),
                    reactions=reactions,
                )
            else:
                ok, detail, reaction_errors = await send_message_to_channel(
                    guild,
                    channel_name,
                    content,
                    embeds=embeds,
                    category_name=category_name,
                    reactions=reactions,
                )
            if ok:
                if reaction_errors:
                    results.append(
                        f"  ⚠️ message → #{channel.name}: sent, but could not add reaction(s): "
                        + ", ".join(reaction_errors)
                    )
                else:
                    results.append(f"  ✅ message → #{channel.name}")
            else:
                results.append(f"  ❌ message → #{channel.name}: {detail}")
        except Exception as exc:
            results.append(f"  ❌ message → #{channel.name}: {exc}")
        await asyncio.sleep(0.5)
    return results


# Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
