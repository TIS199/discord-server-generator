"""Preview and remove a guild's structure for the explicit /nuke command."""

import asyncio
from typing import Dict, List, Tuple

import discord

from src.logger import logger


async def prepare_nuke(guild: discord.Guild) -> Tuple[Dict[str, list], List[str]]:
    """Collect removable items and explain resources the bot cannot manage."""
    plan: Dict[str, list] = {
        "channels": [],
        "roles": [],
        "emojis": [],
        "stickers": [],
        "events": [],
    }
    limitations: List[str] = []
    bot_member = guild.me
    if bot_member is None:
        return plan, ["I could not find the bot's member record in this server."]
    permissions = bot_member.guild_permissions

    if permissions.manage_channels:
        plan["channels"] = list(guild.channels)
    else:
        limitations.append("Manage Channels is missing; channels and their message history cannot be removed.")

    if permissions.manage_roles:
        plan["roles"] = [
            role for role in guild.roles
            if not role.is_default() and not role.managed and role < bot_member.top_role
        ]
        protected = [
            role for role in guild.roles
            if not role.is_default() and not role.managed and role >= bot_member.top_role
        ]
        if protected:
            limitations.append(f"{len(protected)} role(s) are above the bot's highest role and cannot be removed.")
    else:
        limitations.append("Manage Roles is missing; roles cannot be removed.")

    can_manage_expressions = any(
        getattr(permissions, permission, False)
        for permission in ("manage_expressions", "manage_emojis_and_stickers", "manage_emojis")
    )
    if can_manage_expressions:
        plan["emojis"] = list(guild.emojis)
    elif guild.emojis:
        limitations.append("Manage Expressions is missing; server emoji cannot be removed.")

    if can_manage_expressions:
        plan["stickers"] = list(guild.stickers)
    elif guild.stickers:
        limitations.append("Manage Expressions is missing; server stickers cannot be removed.")

    if permissions.manage_events:
        try:
            plan["events"] = await guild.fetch_scheduled_events(with_counts=False)
        except discord.HTTPException as exc:
            limitations.append(f"Scheduled events could not be listed: {exc}")
    elif guild.scheduled_events:
        limitations.append("Manage Events is missing; scheduled events cannot be removed.")

    return plan, limitations


def format_nuke_preview(plan: Dict[str, list], limitations: List[str]) -> str:
    lines = [
        f"**Channels and categories:** {len(plan['channels'])} (channel deletion also removes their messages and threads)",
        f"**Removable roles:** {len(plan['roles'])} (the default role and managed roles are protected)",
        f"**Custom emoji:** {len(plan['emojis'])}",
        f"**Stickers:** {len(plan['stickers'])}",
        f"**Scheduled events:** {len(plan['events'])}",
    ]
    if limitations:
        lines.append("\n**Bot access limits:**\n" + "\n".join(f"• {item}" for item in limitations))
    return "\n".join(lines)


async def nuke_server(plan: Dict[str, list]) -> Tuple[bool, str]:
    """Delete each item in a previously previewed plan and report partial failures."""
    deleted: List[str] = []
    failed: List[str] = []

    async def delete_items(items: list, label: str, *, categories_last: bool = False) -> None:
        if categories_last:
            ordered = sorted(items, key=lambda item: isinstance(item, discord.CategoryChannel))
        else:
            ordered = list(items)
        for item in ordered:
            try:
                await item.delete(reason="Explicit Discord Server Generator /nuke command")
                item_name = getattr(item, "name", str(item))
                deleted.append(f"{label}: {item_name}")
            except discord.HTTPException as exc:
                item_name = getattr(item, "name", str(item))
                failed.append(f"{label} {item_name}: {exc}")
            await asyncio.sleep(0.25)

    # Remove scheduled events before channels in case an event uses a channel.
    await delete_items(plan.get("events", []), "event")
    await delete_items(plan.get("channels", []), "channel", categories_last=True)
    # Higher removable roles are deleted before lower roles; @everyone is absent from the plan.
    await delete_items(sorted(plan.get("roles", []), key=lambda role: role.position, reverse=True), "role")
    await delete_items(plan.get("emojis", []), "emoji")
    await delete_items(plan.get("stickers", []), "sticker")

    lines = [f"**Deleted:** {len(deleted)} server items"]
    lines.extend(f"  ✅ {item}" for item in deleted[:35])
    if len(deleted) > 35:
        lines.append(f"  … and {len(deleted) - 35} more")
    if failed:
        lines.append(f"\n**Could not delete:** {len(failed)}")
        lines.extend(f"  ❌ {item}" for item in failed[:20])
        if len(failed) > 20:
            lines.append(f"  … and {len(failed) - 20} more")
    success = not failed
    logger.warning("/nuke completed: deleted=%d failed=%d", len(deleted), len(failed))
    return success, "\n".join(lines)


# Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
