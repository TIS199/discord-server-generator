"""
builder.py
----------
Reads a validated JSON blueprint and uses discord.py to create
categories, channels, and roles inside a target guild.
"""

import asyncio
from typing import Dict, List, Optional, Tuple

import discord

from src.logger import logger


# ── Permission name → discord.Permissions attribute mapping ──────────────────
_PERM_MAP: Dict[str, str] = {
    "view_channel": "view_channel",
    "send_messages": "send_messages",
    "read_message_history": "read_message_history",
    "manage_messages": "manage_messages",
    "manage_channels": "manage_channels",
    "manage_roles": "manage_roles",
    "kick_members": "kick_members",
    "ban_members": "ban_members",
    "administrator": "administrator",
    "embed_links": "embed_links",
    "attach_files": "attach_files",
    "add_reactions": "add_reactions",
    "use_external_emojis": "use_external_emojis",
    "connect": "connect",
    "speak": "speak",
    "mute_members": "mute_members",
    "deafen_members": "deafen_members",
    "move_members": "move_members",
    "use_voice_activation": "use_voice_activation",
}


def _build_permissions(perm_names: List[str]) -> discord.Permissions:
    kwargs: Dict[str, bool] = {}
    for name in perm_names:
        attr = _PERM_MAP.get(name)
        if attr:
            kwargs[attr] = True
    return discord.Permissions(**kwargs)


def _parse_color(hex_str: str) -> discord.Color:
    try:
        hex_str = hex_str.lstrip("#")
        return discord.Color(int(hex_str, 16))
    except Exception:
        return discord.Color.default()


def _build_overwrites(
    guild: discord.Guild,
    role_map: Dict[str, discord.Role],
    visible_to: List[str],
    hidden_from: List[str],
) -> Dict[discord.Role, discord.PermissionOverwrite]:
    """
    Constructs channel permission overwrites.
    - If visible_to is non-empty: deny @everyone, allow each listed role.
    - hidden_from entries are explicitly denied view_channel.
    """
    overwrites: Dict[discord.Role, discord.PermissionOverwrite] = {}

    if visible_to:
        # Restrict @everyone
        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
        for role_name in visible_to:
            role = role_map.get(role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

    for role_name in hidden_from:
        role = role_map.get(role_name)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=False)

    return overwrites


class BuildResult:
    """Accumulates per-item results for reporting back to the user."""

    def __init__(self) -> None:
        self.created: List[str] = []
        self.failed: List[str] = []

    def ok(self, item: str) -> None:
        self.created.append(item)
        logger.info(f"  ✅ Created: {item}")

    def fail(self, item: str, reason: str) -> None:
        self.failed.append(f"{item}: {reason}")
        logger.warning(f"  ❌ Failed: {item} — {reason}")

    @property
    def success(self) -> bool:
        return len(self.failed) == 0

    def summary(self) -> str:
        lines = [f"**Created ({len(self.created)}):**"]
        for c in self.created:
            lines.append(f"  ✅ {c}")
        if self.failed:
            lines.append(f"\n**Failed ({len(self.failed)}):**")
            for f in self.failed:
                lines.append(f"  ❌ {f}")
        return "\n".join(lines)


async def build_server(
    guild: discord.Guild,
    blueprint: dict,
) -> Tuple[bool, str]:
    """
    Main entry point. Applies the blueprint to *guild*.
    Returns (overall_success, summary_text).
    """
    result = BuildResult()

    # ── 1. Create roles ──────────────────────────────────────────────────────
    role_map: Dict[str, discord.Role] = {}

    # Seed with existing roles so we can reference them in overwrites
    for existing_role in guild.roles:
        role_map[existing_role.name] = existing_role

    for role_def in blueprint.get("roles", []):
        name = role_def.get("name", "").strip()
        if not name:
            continue

        # Skip if role already exists
        if name in role_map and role_map[name] != guild.default_role:
            result.ok(f"role:{name} (already exists, skipped)")
            continue

        try:
            color = _parse_color(role_def.get("color", "#000000"))
            permissions = _build_permissions(role_def.get("permissions", []))
            new_role = await guild.create_role(
                name=name,
                color=color,
                hoist=bool(role_def.get("hoist", False)),
                mentionable=bool(role_def.get("mentionable", False)),
                permissions=permissions,
                reason="Discord Server Generator blueprint",
            )
            role_map[name] = new_role
            result.ok(f"role:{name}")
        except discord.HTTPException as exc:
            result.fail(f"role:{name}", str(exc))
        except Exception as exc:
            result.fail(f"role:{name}", str(exc))

    # ── 2. Create categories & channels ─────────────────────────────────────
    for cat_def in blueprint.get("categories", []):
        cat_name = cat_def.get("name", "").strip()
        if not cat_name:
            continue

        cat_visible_to: List[str] = cat_def.get("visible_to", [])
        cat_overwrites = _build_overwrites(guild, role_map, cat_visible_to, [])

        try:
            category = await guild.create_category(
                name=cat_name,
                overwrites=cat_overwrites,
                reason="Discord Server Generator blueprint",
            )
            result.ok(f"category:{cat_name}")
        except discord.HTTPException as exc:
            result.fail(f"category:{cat_name}", str(exc))
            category = None

        for ch_def in cat_def.get("channels", []):
            ch_name = ch_def.get("name", "").strip()
            if not ch_name:
                continue

            ch_type = ch_def.get("type", "text")
            ch_visible_to: List[str] = ch_def.get("visible_to", [])
            ch_hidden_from: List[str] = ch_def.get("hidden_from", [])

            # Channel-level overwrites; fall back to category overwrites if not set
            if ch_visible_to or ch_hidden_from:
                ch_overwrites = _build_overwrites(guild, role_map, ch_visible_to, ch_hidden_from)
            else:
                ch_overwrites = cat_overwrites.copy()

            try:
                if ch_type == "voice":
                    await guild.create_voice_channel(
                        name=ch_name,
                        category=category,
                        overwrites=ch_overwrites,
                        reason="Discord Server Generator blueprint",
                    )
                else:
                    await guild.create_text_channel(
                        name=ch_name,
                        category=category,
                        topic=ch_def.get("topic") or "",
                        slowmode_delay=int(ch_def.get("slowmode", 0)),
                        nsfw=bool(ch_def.get("nsfw", False)),
                        overwrites=ch_overwrites,
                        reason="Discord Server Generator blueprint",
                    )
                result.ok(f"{ch_type}-channel:{cat_name}/{ch_name}")
            except discord.HTTPException as exc:
                result.fail(f"{ch_type}-channel:{cat_name}/{ch_name}", str(exc))
            except Exception as exc:
                result.fail(f"{ch_type}-channel:{cat_name}/{ch_name}", str(exc))

            # Small delay to avoid hitting Discord rate limits
            await asyncio.sleep(0.4)

    return result.success, result.summary()


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
