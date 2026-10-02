"""Apply an approved JSON blueprint to a Discord guild."""

import asyncio
from typing import Dict, List, Optional, Tuple

import discord

from src.logger import logger
from src.sender import process_messages


def _build_permissions(permission_names: List[str]) -> discord.Permissions:
    """Role permissions are an allow-list: every unlisted permission is disabled."""
    return discord.Permissions(**{name: True for name in permission_names})


def _parse_color(hex_color: str) -> discord.Color:
    try:
        value = hex_color.lstrip("#")
        if len(value) == 3:
            value = "".join(character * 2 for character in value)
        return discord.Color(int(value, 16))
    except (TypeError, ValueError):
        return discord.Color.default()


def _apply_overwrite_values(
    overwrites: Dict[discord.Role, discord.PermissionOverwrite],
    role: discord.Role,
    values: Dict[str, Optional[bool]],
) -> None:
    overwrite = overwrites.get(role, discord.PermissionOverwrite())
    for permission, value in values.items():
        setattr(overwrite, permission, value)
    if overwrite.is_empty():
        overwrites.pop(role, None)
    else:
        overwrites[role] = overwrite


def _build_overwrites(
    guild: discord.Guild,
    role_map: Dict[str, discord.Role],
    *,
    base: Optional[Dict[discord.Role, discord.PermissionOverwrite]] = None,
    visible_to: Optional[List[str]] = None,
    hidden_from: Optional[List[str]] = None,
    permission_overwrites: Optional[Dict[str, Dict[str, Optional[bool]]]] = None,
) -> Dict[discord.Role, discord.PermissionOverwrite]:
    """Copy inherited overwrites and apply the blueprint's role-level changes."""
    overwrites = dict(base or {})
    visible_to = visible_to or []
    hidden_from = hidden_from or []

    if visible_to:
        _apply_overwrite_values(overwrites, guild.default_role, {"view_channel": False})
        for role_name in visible_to:
            role = role_map.get(role_name)
            if role is None:
                raise ValueError(f"Role '{role_name}' was not created or found on the server")
            _apply_overwrite_values(overwrites, role, {"view_channel": True})

    for role_name in hidden_from:
        role = role_map.get(role_name)
        if role is None:
            raise ValueError(f"Role '{role_name}' was not created or found on the server")
        _apply_overwrite_values(overwrites, role, {"view_channel": False})

    for role_name, values in (permission_overwrites or {}).items():
        role = role_map.get(role_name)
        if role is None:
            raise ValueError(f"Role '{role_name}' was not created or found on the server")
        # Null means inherit, so retain a category overwrite when one exists.
        explicit_values = {permission: value for permission, value in values.items() if value is not None}
        if explicit_values:
            _apply_overwrite_values(overwrites, role, explicit_values)

    return overwrites


def _channel_matches_type(channel: discord.abc.GuildChannel, channel_type: str) -> bool:
    if channel_type == "text":
        return isinstance(channel, discord.TextChannel) and channel.type == discord.ChannelType.text
    if channel_type == "announcement":
        return isinstance(channel, discord.TextChannel) and channel.type == discord.ChannelType.news
    if channel_type == "voice":
        return isinstance(channel, discord.VoiceChannel) and not isinstance(channel, discord.StageChannel)
    if channel_type == "stage":
        return isinstance(channel, discord.StageChannel)
    if channel_type == "forum":
        return isinstance(channel, discord.ForumChannel)
    return False


class BuildResult:
    """Accumulate success and failure details for the build report."""

    def __init__(self) -> None:
        self.created: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []

    def ok(self, item: str) -> None:
        self.created.append(item)
        logger.info("Created: %s", item)

    def fail(self, item: str, reason: str) -> None:
        self.failed.append(f"{item}: {reason}")
        logger.warning("Failed: %s — %s", item, reason)

    def warn(self, item: str) -> None:
        self.warnings.append(item)
        logger.warning("Warning: %s", item)

    @property
    def success(self) -> bool:
        return not self.failed

    def summary(self) -> str:
        lines = [f"**Completed ({len(self.created)}):**"]
        lines.extend(f"  ✅ {item}" for item in self.created)
        if self.failed:
            lines.append(f"\n**Needs attention ({len(self.failed)}):**")
            lines.extend(f"  ❌ {item}" for item in self.failed)
        if self.warnings:
            lines.append(f"\n**Warnings ({len(self.warnings)}):**")
            lines.extend(f"  ⚠️ {item}" for item in self.warnings)
        return "\n".join(lines)


async def _configure_guild(
    guild: discord.Guild,
    settings: dict,
    result: BuildResult,
) -> None:
    if not settings:
        return
    enum_fields = {
        "verification_level": discord.VerificationLevel,
        "default_notifications": discord.NotificationLevel,
        "explicit_content_filter": discord.ContentFilter,
    }
    edit_values = {key: value for key, value in settings.items() if key not in {"preferred_locale"}}
    try:
        for field, enum_class in enum_fields.items():
            if field in edit_values:
                edit_values[field] = getattr(enum_class, edit_values[field])
        if "preferred_locale" in settings:
            edit_values["preferred_locale"] = discord.Locale(settings["preferred_locale"])
        await guild.edit(reason="Discord Server Generator blueprint", **edit_values)
        result.ok("guild settings")
    except (discord.HTTPException, AttributeError, ValueError, TypeError) as exc:
        result.fail("guild settings", str(exc))


async def build_server(guild: discord.Guild, blueprint: dict) -> Tuple[bool, str]:
    """Apply guild settings, configure roles, create structure, and post messages."""
    result = BuildResult()

    await _configure_guild(guild, blueprint.get("guild_settings", {}), result)

    # Include existing guild roles so overrides may target roles omitted from the blueprint.
    role_map: Dict[str, discord.Role] = {role.name: role for role in guild.roles}
    role_defs = blueprint.get("roles", [])

    for role_def in role_defs:
        name = role_def.get("name", "").strip()
        if not name:
            continue
        existing = role_map.get(name)
        update_existing = bool(role_def.get("update_existing", True))
        if existing and existing != guild.default_role and not update_existing:
            result.ok(f"role:{name} (already exists, skipped)")
            continue

        role_options = {"reason": "Discord Server Generator blueprint"}
        if existing and existing != guild.default_role:
            if "color" in role_def:
                role_options["color"] = _parse_color(role_def["color"])
            if "hoist" in role_def:
                role_options["hoist"] = role_def["hoist"]
            if "mentionable" in role_def:
                role_options["mentionable"] = role_def["mentionable"]
            if "permissions" in role_def:
                role_options["permissions"] = _build_permissions(role_def["permissions"])
        else:
            role_options.update({
                "color": _parse_color(role_def.get("color", "#000000")),
                "hoist": bool(role_def.get("hoist", False)),
                "mentionable": bool(role_def.get("mentionable", False)),
                "permissions": _build_permissions(role_def.get("permissions", [])),
            })
        try:
            if existing and existing != guild.default_role:
                if len(role_options) == 1:
                    result.ok(f"role:{name} (already exists, no settings supplied)")
                    continue
                if existing.managed:
                    result.fail(f"role:{name}", "Discord-managed roles cannot be edited")
                    continue
                await existing.edit(**role_options)
                role_map[name] = existing
                result.ok(f"role:{name} (updated)")
            else:
                created = await guild.create_role(name=name, **role_options)
                role_map[name] = created
                result.ok(f"role:{name}")
        except discord.HTTPException as exc:
            result.fail(f"role:{name}", str(exc))
        except Exception as exc:
            result.fail(f"role:{name}", str(exc))

    # Reuse matching categories and channels so applying a blueprint again updates
    # the existing structure instead of creating duplicates.
    for category_def in blueprint.get("categories", []):
        category_name = category_def.get("name", "").strip()
        if not category_name:
            continue
        try:
            category_has_permissions = (
                "visible_to" in category_def or "permission_overwrites" in category_def
            )
            category_overwrites = _build_overwrites(
                guild,
                role_map,
                visible_to=category_def.get("visible_to", []),
                permission_overwrites=category_def.get("permission_overwrites", {}),
            )
            category = discord.utils.get(guild.categories, name=category_name)
            is_existing_category = category is not None
            if category:
                if category_has_permissions:
                    category = await category.edit(
                        overwrites=category_overwrites,
                        reason="Discord Server Generator blueprint",
                    ) or category
                    result.ok(f"category:{category_name} (updated)")
                else:
                    result.ok(f"category:{category_name} (reused)")
            else:
                category = await guild.create_category(
                    name=category_name,
                    overwrites=category_overwrites,
                    reason="Discord Server Generator blueprint",
                )
                result.ok(f"category:{category_name}")
            inherited_overwrites = (
                category_overwrites
                if category_has_permissions or not is_existing_category
                else dict(category.overwrites)
            )
        except Exception as exc:
            result.fail(f"category:{category_name}", str(exc))
            continue

        for channel_def in category_def.get("channels", []):
            channel_name = channel_def.get("name", "").strip()
            if not channel_name:
                continue
            channel_type = channel_def.get("type", "text")

            try:
                visible_to = channel_def.get("visible_to", [])
                hidden_from = channel_def.get("hidden_from", [])
                channel_has_permissions = bool(visible_to or hidden_from) or "permission_overwrites" in channel_def
                inherit_category = not bool(visible_to)
                channel_overwrites = _build_overwrites(
                    guild,
                    role_map,
                    base=inherited_overwrites if inherit_category else {},
                    visible_to=visible_to,
                    hidden_from=hidden_from,
                    permission_overwrites=channel_def.get("permission_overwrites", {}),
                )
                common = {
                    "category": category,
                    "overwrites": channel_overwrites,
                    "reason": "Discord Server Generator blueprint",
                }
                slowmode = int(channel_def.get("slowmode", 0))
                nsfw = bool(channel_def.get("nsfw", False))
                existing_channel = discord.utils.get(category.channels, name=channel_name)
                if existing_channel:
                    if not _channel_matches_type(existing_channel, channel_type):
                        result.fail(
                            f"{channel_type}-channel:{category_name}/{channel_name}",
                            f"a channel with this name already exists as {existing_channel.type}",
                        )
                        continue
                    edit_options = {
                        "reason": "Discord Server Generator blueprint",
                    }
                    if category_has_permissions or channel_has_permissions:
                        edit_options["overwrites"] = channel_overwrites
                    for field, option in (
                        ("topic", "topic"),
                        ("slowmode", "slowmode_delay"),
                        ("nsfw", "nsfw"),
                        ("bitrate", "bitrate"),
                        ("user_limit", "user_limit"),
                        ("default_auto_archive_duration", "default_auto_archive_duration"),
                        ("default_thread_slowmode_delay", "default_thread_slowmode_delay"),
                    ):
                        if field in channel_def:
                            edit_options[option] = channel_def[field]
                    if len(edit_options) == 1:
                        result.ok(f"{channel_type}-channel:{category_name}/{channel_name} (reused)")
                    else:
                        await existing_channel.edit(**edit_options)
                        result.ok(f"{channel_type}-channel:{category_name}/{channel_name} (updated)")
                elif channel_type in {"text", "announcement"}:
                    await guild.create_text_channel(
                        name=channel_name,
                        topic=channel_def.get("topic") or "",
                        slowmode_delay=slowmode,
                        nsfw=nsfw,
                        news=channel_type == "announcement",
                        default_auto_archive_duration=int(channel_def.get("default_auto_archive_duration", 1440)),
                        default_thread_slowmode_delay=int(channel_def.get("default_thread_slowmode_delay", 0)),
                        **common,
                    )
                    result.ok(f"{channel_type}-channel:{category_name}/{channel_name}")
                elif channel_type == "voice":
                    await guild.create_voice_channel(
                        name=channel_name,
                        bitrate=int(channel_def.get("bitrate", 64000)),
                        user_limit=int(channel_def.get("user_limit", 0)),
                        nsfw=nsfw,
                        **common,
                    )
                    result.ok(f"{channel_type}-channel:{category_name}/{channel_name}")
                elif channel_type == "stage":
                    await guild.create_stage_channel(
                        name=channel_name,
                        bitrate=int(channel_def.get("bitrate", 64000)),
                        user_limit=int(channel_def.get("user_limit", 0)),
                        nsfw=nsfw,
                        **common,
                    )
                    result.ok(f"{channel_type}-channel:{category_name}/{channel_name}")
                elif channel_type == "forum":
                    await guild.create_forum(
                        name=channel_name,
                        topic=channel_def.get("topic") or "",
                        slowmode_delay=slowmode,
                        nsfw=nsfw,
                        default_auto_archive_duration=int(channel_def.get("default_auto_archive_duration", 1440)),
                        default_thread_slowmode_delay=int(channel_def.get("default_thread_slowmode_delay", 0)),
                        **common,
                    )
                    result.ok(f"{channel_type}-channel:{category_name}/{channel_name}")
            except discord.HTTPException as exc:
                result.fail(f"{channel_type}-channel:{category_name}/{channel_name}", str(exc))
            except Exception as exc:
                result.fail(f"{channel_type}-channel:{category_name}/{channel_name}", str(exc))
            await asyncio.sleep(0.4)

    messages = blueprint.get("messages", [])
    if messages:
        for message_result in await process_messages(guild, messages):
            if message_result.startswith("  ✅"):
                result.ok(message_result[4:].strip())
            elif message_result.startswith("  ⚠️"):
                result.warn(message_result[4:].strip())
            else:
                result.fail(message_result[4:].strip(), "Message could not be sent")

    return result.success, result.summary()


# Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
