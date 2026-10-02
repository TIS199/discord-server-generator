"""Validate blueprint JSON before it is shown for approval or applied."""

from datetime import datetime
import re
from typing import Any, List, Optional, Set, Tuple
from urllib.parse import urlsplit

import discord


VALID_PERMISSIONS: Set[str] = set(discord.Permissions.VALID_FLAGS)
VALID_CHANNEL_TYPES = {"text", "announcement", "voice", "stage", "forum"}
VALID_VERIFICATION_LEVELS = {"none", "low", "medium", "high", "highest"}
VALID_NOTIFICATION_LEVELS = {"all_messages", "only_mentions"}
VALID_CONTENT_FILTERS = {"disabled", "no_role", "all_members"}
VALID_AUTO_ARCHIVE_DURATIONS = {60, 1440, 4320, 10080}
VALID_LOCALES = {locale.value for locale in discord.Locale}


def _check_str(value: Any, path: str, errors: List[str], *, allow_empty: bool = False) -> bool:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        qualifier = "a string" if allow_empty else "a non-empty string"
        errors.append(f"{path}: must be {qualifier}")
        return False
    return True


def _check_bool(value: Any, path: str, errors: List[str]) -> None:
    if not isinstance(value, bool):
        errors.append(f"{path}: must be a boolean (true/false)")


def _check_int(value: Any, path: str, errors: List[str], minimum: int, maximum: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        errors.append(f"{path}: must be an integer between {minimum} and {maximum}")


def _reject_unknown_fields(value: dict, allowed: Set[str], path: str, errors: List[str]) -> None:
    for field in value:
        if field not in allowed:
            errors.append(f"{path}.{field}: unknown field")


def _check_url(value: Any, path: str, errors: List[str]) -> None:
    if not _check_str(value, path, errors):
        return
    try:
        parsed = urlsplit(value)
    except ValueError:
        errors.append(f"{path}: must be a complete HTTP or HTTPS URL")
        return
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        errors.append(f"{path}: must be a complete HTTP or HTTPS URL")


def _known_roles(
    role_names: Set[str], existing_role_names: Optional[Set[str]]
) -> Set[str]:
    known = set(role_names)
    known.add("@everyone")
    if existing_role_names:
        known.update(existing_role_names)
    return known


def _validate_role_references(
    names: Any,
    path: str,
    errors: List[str],
    known_roles: Set[str],
) -> None:
    if not isinstance(names, list):
        errors.append(f"{path}: must be a list of role names")
        return
    for role_name in names:
        if not isinstance(role_name, str) or role_name not in known_roles:
            errors.append(f"{path}: role {role_name!r} is not defined or present on the server")


def _validate_overwrites(
    overwrites: Any,
    path: str,
    errors: List[str],
    known_roles: Set[str],
) -> None:
    if not isinstance(overwrites, dict):
        errors.append(f"{path}: must be an object mapping role names to permission objects")
        return

    for role_name, permissions in overwrites.items():
        if not isinstance(role_name, str) or not role_name.strip():
            errors.append(f"{path}: role names must be non-empty strings")
        elif role_name not in known_roles:
            errors.append(f"{path}: role {role_name!r} is not defined or present on the server")
        if not isinstance(permissions, dict):
            errors.append(f"{path}.{role_name}: must be an object of permission booleans")
            continue
        for permission, value in permissions.items():
            if not isinstance(permission, str) or permission not in VALID_PERMISSIONS:
                errors.append(f"{path}.{role_name}: unknown permission {permission!r}")
            if value is not None and not isinstance(value, bool):
                errors.append(f"{path}.{role_name}.{permission}: must be true, false, or null")


def _validate_channel(
    channel: Any,
    index: int,
    category_name: str,
    known_roles: Set[str],
    errors: List[str],
) -> None:
    path = f"categories[{category_name!r}].channels[{index}]"
    if not isinstance(channel, dict):
        errors.append(f"{path}: must be an object")
        return
    _reject_unknown_fields(
        channel,
        {
            "name", "type", "topic", "slowmode", "nsfw", "bitrate", "user_limit",
            "default_auto_archive_duration", "default_thread_slowmode_delay", "visible_to",
            "hidden_from", "permission_overwrites",
        },
        path,
        errors,
    )

    channel_name = channel.get("name")
    if _check_str(channel_name, f"{path}.name", errors) and len(channel_name) > 100:
        errors.append(f"{path}.name: must be at most 100 characters")
    channel_type = channel.get("type", "text")
    supports_text_settings = isinstance(channel_type, str) and channel_type in {"text", "announcement", "forum"}
    supports_voice_settings = isinstance(channel_type, str) and channel_type in {"voice", "stage"}
    if not isinstance(channel_type, str) or channel_type not in VALID_CHANNEL_TYPES:
        errors.append(f"{path}.type: must be one of {', '.join(sorted(VALID_CHANNEL_TYPES))}")

    if "topic" in channel:
        _check_str(channel["topic"], f"{path}.topic", errors, allow_empty=True)
        if isinstance(channel["topic"], str) and len(channel["topic"]) > 1024:
            errors.append(f"{path}.topic: must be at most 1024 characters")
        if not supports_text_settings and channel["topic"]:
            errors.append(f"{path}.topic: only text, announcement, and forum channels support topics")

    slowmode = channel.get("slowmode", 0)
    _check_int(slowmode, f"{path}.slowmode", errors, 0, 21600)
    if not supports_text_settings and slowmode:
        errors.append(f"{path}.slowmode: only text, announcement, and forum channels support slowmode")

    if "nsfw" in channel:
        _check_bool(channel["nsfw"], f"{path}.nsfw", errors)
    if "bitrate" in channel:
        _check_int(channel["bitrate"], f"{path}.bitrate", errors, 8000, 384000)
        if not supports_voice_settings:
            errors.append(f"{path}.bitrate: only voice and stage channels support bitrate")
    if "user_limit" in channel:
        _check_int(channel["user_limit"], f"{path}.user_limit", errors, 0, 99)
        if not supports_voice_settings:
            errors.append(f"{path}.user_limit: only voice and stage channels support user_limit")
    if "default_auto_archive_duration" in channel:
        duration = channel["default_auto_archive_duration"]
        if not isinstance(duration, int) or isinstance(duration, bool) or duration not in VALID_AUTO_ARCHIVE_DURATIONS:
            errors.append(f"{path}.default_auto_archive_duration: must be one of 60, 1440, 4320, or 10080")
        if not supports_text_settings:
            errors.append(f"{path}.default_auto_archive_duration: only text, announcement, and forum channels support threads")
    if "default_thread_slowmode_delay" in channel:
        _check_int(channel["default_thread_slowmode_delay"], f"{path}.default_thread_slowmode_delay", errors, 0, 21600)
        if not supports_text_settings:
            errors.append(f"{path}.default_thread_slowmode_delay: only text, announcement, and forum channels support threads")

    _validate_role_references(channel.get("visible_to", []), f"{path}.visible_to", errors, known_roles)
    _validate_role_references(channel.get("hidden_from", []), f"{path}.hidden_from", errors, known_roles)
    if "permission_overwrites" in channel:
        _validate_overwrites(channel["permission_overwrites"], f"{path}.permission_overwrites", errors, known_roles)


def _validate_category(
    category: Any,
    index: int,
    known_roles: Set[str],
    errors: List[str],
) -> None:
    path = f"categories[{index}]"
    if not isinstance(category, dict):
        errors.append(f"{path}: must be an object")
        return
    _reject_unknown_fields(category, {"name", "visible_to", "permission_overwrites", "channels"}, path, errors)
    if not _check_str(category.get("name"), f"{path}.name", errors):
        return

    category_name = category["name"]
    if len(category_name) > 100:
        errors.append(f"{path}.name: must be at most 100 characters")
    _validate_role_references(category.get("visible_to", []), f"{path}.visible_to", errors, known_roles)
    if "permission_overwrites" in category:
        _validate_overwrites(category["permission_overwrites"], f"{path}.permission_overwrites", errors, known_roles)

    channels = category.get("channels", [])
    if not isinstance(channels, list):
        errors.append(f"{path}.channels: must be a list")
        return
    seen_channel_names: Set[str] = set()
    for channel_index, channel in enumerate(channels):
        if isinstance(channel, dict) and isinstance(channel.get("name"), str):
            name = channel["name"]
            if name in seen_channel_names:
                errors.append(f"{path}.channels[{channel_index}].name: duplicate channel name {name!r}")
            seen_channel_names.add(name)
        _validate_channel(channel, channel_index, category_name, known_roles, errors)


def _validate_role(role: Any, index: int, errors: List[str]) -> None:
    path = f"roles[{index}]"
    if not isinstance(role, dict):
        errors.append(f"{path}: must be an object")
        return
    _reject_unknown_fields(role, {"name", "color", "hoist", "mentionable", "update_existing", "permissions"}, path, errors)
    if not _check_str(role.get("name"), f"{path}.name", errors):
        return
    if len(role["name"]) > 100:
        errors.append(f"{path}.name: must be at most 100 characters")
    if role["name"] == "@everyone":
        errors.append(f"{path}.name: @everyone is managed by Discord and cannot be configured as a role")

    color = role.get("color", "#000000")
    if not isinstance(color, str) or not re.fullmatch(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})", color):
        errors.append(f"{path}.color: must be a hex color like '#FF5733'")

    for field in ("hoist", "mentionable", "update_existing"):
        if field in role:
            _check_bool(role[field], f"{path}.{field}", errors)

    permissions = role.get("permissions", [])
    if not isinstance(permissions, list):
        errors.append(f"{path}.permissions: must be a list of permission names")
    else:
        for permission in permissions:
            if not isinstance(permission, str) or permission not in VALID_PERMISSIONS:
                errors.append(f"{path}.permissions: unknown permission {permission!r}")


def _validate_guild_settings(settings: Any, errors: List[str]) -> None:
    path = "guild_settings"
    if not isinstance(settings, dict):
        errors.append(f"{path}: must be an object")
        return
    _reject_unknown_fields(
        settings,
        {
            "name", "description", "verification_level", "default_notifications",
            "explicit_content_filter", "afk_timeout", "preferred_locale",
            "premium_progress_bar_enabled",
        },
        path,
        errors,
    )

    if "name" in settings:
        name = settings["name"]
        if _check_str(name, f"{path}.name", errors) and len(name) > 100:
            errors.append(f"{path}.name: must be at most 100 characters")
    if "description" in settings:
        description = settings["description"]
        if _check_str(description, f"{path}.description", errors, allow_empty=True) and len(description) > 120:
            errors.append(f"{path}.description: must be at most 120 characters")

    choices = {
        "verification_level": VALID_VERIFICATION_LEVELS,
        "default_notifications": VALID_NOTIFICATION_LEVELS,
        "explicit_content_filter": VALID_CONTENT_FILTERS,
    }
    for field, allowed in choices.items():
        if field in settings and (
            not isinstance(settings[field], str) or settings[field] not in allowed
        ):
            errors.append(f"{path}.{field}: must be one of {', '.join(sorted(allowed))}")
    if "afk_timeout" in settings and (
        not isinstance(settings["afk_timeout"], int)
        or isinstance(settings["afk_timeout"], bool)
        or settings["afk_timeout"] not in {60, 300, 900, 1800, 3600}
    ):
        errors.append(f"{path}.afk_timeout: must be one of 60, 300, 900, 1800, or 3600 seconds")
    if "preferred_locale" in settings:
        locale = settings["preferred_locale"]
        if _check_str(locale, f"{path}.preferred_locale", errors) and locale not in VALID_LOCALES:
            errors.append(f"{path}.preferred_locale: must be a Discord locale such as en-US")
    if "premium_progress_bar_enabled" in settings:
        _check_bool(settings["premium_progress_bar_enabled"], f"{path}.premium_progress_bar_enabled", errors)


def _validate_embed(embed: Any, path: str, errors: List[str]) -> int:
    if not isinstance(embed, dict):
        errors.append(f"{path}: must be an object")
        return 0
    _reject_unknown_fields(
        embed,
        {"title", "description", "url", "color", "author", "footer", "thumbnail_url", "image_url", "fields", "timestamp"},
        path,
        errors,
    )
    text_fields = {"title": 256, "description": 4096, "url": 2048, "thumbnail_url": 2048, "image_url": 2048}
    total_text = 0
    has_content = False
    for field, limit in text_fields.items():
        if field not in embed:
            continue
        value = embed[field]
        if field in {"url", "thumbnail_url", "image_url"}:
            _check_url(value, f"{path}.{field}", errors)
        else:
            _check_str(value, f"{path}.{field}", errors)
        if isinstance(value, str) and value.strip():
            total_text += len(value) if field not in {"url", "thumbnail_url", "image_url"} else 0
            if field in {"title", "description"}:
                has_content = True
            if len(value) > limit:
                errors.append(f"{path}.{field}: must be at most {limit} characters")

    if "color" in embed:
        color = embed["color"]
        if isinstance(color, str):
            if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", color):
                errors.append(f"{path}.color: must be a six-digit hex color such as '#5865F2'")
        elif not isinstance(color, int) or isinstance(color, bool) or not 0 <= color <= 0xFFFFFF:
            errors.append(f"{path}.color: must be a hex color or integer from 0 to 16777215")

    for group, max_text in (("author", 256), ("footer", 2048)):
        if group not in embed:
            continue
        value = embed[group]
        if not isinstance(value, dict):
            errors.append(f"{path}.{group}: must be an object")
            continue
        allowed_group_fields = {"name", "url", "icon_url"} if group == "author" else {"text", "icon_url"}
        _reject_unknown_fields(value, allowed_group_fields, f"{path}.{group}", errors)
        text = value.get("name" if group == "author" else "text")
        if _check_str(text, f"{path}.{group}.{('name' if group == 'author' else 'text')}", errors):
            total_text += len(text)
            has_content = True
            if len(text) > max_text:
                errors.append(f"{path}.{group}: text must be at most {max_text} characters")
        for url_field in (("url", "icon_url") if group == "author" else ("icon_url",)):
            if url_field in value:
                _check_url(value[url_field], f"{path}.{group}.{url_field}", errors)

    if "fields" in embed:
        fields = embed["fields"]
        if not isinstance(fields, list):
            errors.append(f"{path}.fields: must be a list")
        else:
            if len(fields) > 25:
                errors.append(f"{path}.fields: Discord allows at most 25 fields per embed")
            for index, field in enumerate(fields):
                field_path = f"{path}.fields[{index}]"
                if not isinstance(field, dict):
                    errors.append(f"{field_path}: must be an object")
                    continue
                _reject_unknown_fields(field, {"name", "value", "inline"}, field_path, errors)
                name = field.get("name")
                value = field.get("value")
                if _check_str(name, f"{field_path}.name", errors) and len(name) > 256:
                    errors.append(f"{field_path}.name: must be at most 256 characters")
                if _check_str(value, f"{field_path}.value", errors) and len(value) > 1024:
                    errors.append(f"{field_path}.value: must be at most 1024 characters")
                if isinstance(name, str) and isinstance(value, str):
                    total_text += len(name) + len(value)
                    has_content = True
                if "inline" in field:
                    _check_bool(field["inline"], f"{field_path}.inline", errors)

    if "timestamp" in embed:
        timestamp = embed["timestamp"]
        if not isinstance(timestamp, str):
            errors.append(f"{path}.timestamp: must be an ISO 8601 date-time string")
        else:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{path}.timestamp: must be an ISO 8601 date-time string")

    if not has_content:
        errors.append(f"{path}: include a title, description, author, footer, or at least one field")
    if total_text > 6000:
        errors.append(f"{path}: combined text must be at most 6000 characters")
    return total_text


def _validate_messages(messages: Any, errors: List[str]) -> None:
    if not isinstance(messages, list):
        errors.append("messages: must be a list")
        return
    for index, message in enumerate(messages):
        path = f"messages[{index}]"
        if not isinstance(message, dict):
            errors.append(f"{path}: must be an object")
            continue
        _reject_unknown_fields(
            message,
            {
                "channel", "category", "content", "embed", "embeds", "reactions",
                "use_webhook", "webhook_name", "webhook_avatar_url",
            },
            path,
            errors,
        )
        _check_str(message.get("channel"), f"{path}.channel", errors)
        if "category" in message:
            _check_str(message["category"], f"{path}.category", errors)
        content = message.get("content", "")
        if not isinstance(content, str):
            errors.append(f"{path}.content: must be a string")
        elif len(content) > 10000:
            errors.append(f"{path}.content: must be at most 10000 characters")
        has_embeds = False
        embed_count = 0
        combined_embed_text = 0
        if "embed" in message:
            combined_embed_text += _validate_embed(message["embed"], f"{path}.embed", errors)
            embed_count += 1
            has_embeds = True
        if "embeds" in message:
            embeds = message["embeds"]
            if not isinstance(embeds, list) or not embeds:
                errors.append(f"{path}.embeds: must be a non-empty list")
            else:
                if len(embeds) > 10:
                    errors.append(f"{path}.embeds: Discord allows at most 10 embeds per message")
                for embed_index, embed in enumerate(embeds[:10]):
                    combined_embed_text += _validate_embed(embed, f"{path}.embeds[{embed_index}]", errors)
                embed_count += len(embeds)
                has_embeds = True
        if "embed" in message and "embeds" in message:
            errors.append(f"{path}: use either embed or embeds, not both")
        if embed_count > 10:
            errors.append(f"{path}: Discord allows at most 10 embeds per message")
        if combined_embed_text > 6000:
            errors.append(f"{path}: combined embed text must be at most 6000 characters")
        if (not isinstance(content, str) or not content.strip()) and not has_embeds:
            errors.append(f"{path}: include non-empty content or at least one embed")
        if "reactions" in message:
            reactions = message["reactions"]
            if not isinstance(reactions, list):
                errors.append(f"{path}.reactions: must be a list of emoji strings")
            else:
                if len(reactions) > 20:
                    errors.append(f"{path}.reactions: Discord allows at most 20 reactions per message")
                seen_reactions: Set[str] = set()
                for reaction_index, reaction in enumerate(reactions):
                    reaction_path = f"{path}.reactions[{reaction_index}]"
                    if _check_str(reaction, reaction_path, errors):
                        if len(reaction) > 100:
                            errors.append(f"{reaction_path}: must be at most 100 characters")
                        if reaction in seen_reactions:
                            errors.append(f"{reaction_path}: duplicate reaction")
                        seen_reactions.add(reaction)
        if "use_webhook" in message:
            _check_bool(message["use_webhook"], f"{path}.use_webhook", errors)
        if "webhook_name" in message:
            webhook_name = message["webhook_name"]
            if _check_str(webhook_name, f"{path}.webhook_name", errors) and len(webhook_name) > 80:
                errors.append(f"{path}.webhook_name: must be at most 80 characters")
        if "webhook_avatar_url" in message and message["webhook_avatar_url"] is not None:
            _check_url(message["webhook_avatar_url"], f"{path}.webhook_avatar_url", errors)


def validate(
    blueprint: Any,
    existing_role_names: Optional[Set[str]] = None,
) -> Tuple[bool, List[str]]:
    """Return (valid, errors), optionally checking references against a guild's roles."""
    errors: List[str] = []
    if not isinstance(blueprint, dict):
        return False, ["Blueprint must be a JSON object"]
    _reject_unknown_fields(
        blueprint,
        {"server_name", "server_description", "guild_settings", "roles", "categories", "messages"},
        "blueprint",
        errors,
    )

    server_name = blueprint.get("server_name")
    if _check_str(server_name, "server_name", errors) and len(server_name) > 100:
        errors.append("server_name: must be at most 100 characters")
    if "server_description" in blueprint:
        description = blueprint["server_description"]
        if _check_str(description, "server_description", errors, allow_empty=True) and len(description) > 500:
            errors.append("server_description: must be at most 500 characters")

    roles = blueprint.get("roles", [])
    role_names: Set[str] = set()
    if not isinstance(roles, list):
        errors.append("roles: must be a list")
    else:
        for index, role in enumerate(roles):
            _validate_role(role, index, errors)
            if isinstance(role, dict) and isinstance(role.get("name"), str):
                if role["name"] in role_names:
                    errors.append(f"roles[{index}].name: duplicate role name {role['name']!r}")
                role_names.add(role["name"])

    known_roles = _known_roles(role_names, existing_role_names)

    categories = blueprint.get("categories", [])
    if not isinstance(categories, list):
        errors.append("categories: must be a list")
    else:
        category_names: Set[str] = set()
        for index, category in enumerate(categories):
            if isinstance(category, dict) and isinstance(category.get("name"), str):
                name = category["name"]
                if name in category_names:
                    errors.append(f"categories[{index}].name: duplicate category name {name!r}")
                category_names.add(name)
            _validate_category(category, index, known_roles, errors)

    if "guild_settings" in blueprint:
        _validate_guild_settings(blueprint["guild_settings"], errors)
    if "messages" in blueprint:
        _validate_messages(blueprint["messages"], errors)
    if not categories and not roles and not blueprint.get("guild_settings") and not blueprint.get("messages"):
        errors.append("blueprint: include at least one role, category, guild setting, or message")

    return len(errors) == 0, errors


# Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
