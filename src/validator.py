"""
validator.py
------------
Validates a parsed blueprint dict against the expected schema.
Returns (is_valid: bool, errors: list[str]).
No code execution — pure data validation.
"""

from typing import Any, Dict, List, Tuple

VALID_PERMISSIONS = {
    "view_channel", "send_messages", "read_message_history", "manage_messages",
    "manage_channels", "manage_roles", "kick_members", "ban_members",
    "administrator", "embed_links", "attach_files", "add_reactions",
    "use_external_emojis", "connect", "speak", "mute_members", "deafen_members",
    "move_members", "use_voice_activation",
}

VALID_CHANNEL_TYPES = {"text", "voice"}


def _check_str(val: Any, path: str, errors: List[str]) -> bool:
    if not isinstance(val, str) or not val.strip():
        errors.append(f"{path}: must be a non-empty string")
        return False
    return True


def _check_bool(val: Any, path: str, errors: List[str]) -> None:
    if not isinstance(val, bool):
        errors.append(f"{path}: must be a boolean (true/false)")


def _check_int(val: Any, path: str, errors: List[str]) -> None:
    if not isinstance(val, int) or isinstance(val, bool):
        errors.append(f"{path}: must be an integer")


def _validate_channel(ch: Any, idx: int, cat_name: str, role_names: set, errors: List[str]) -> None:
    path = f"categories[{cat_name!r}].channels[{idx}]"
    if not isinstance(ch, dict):
        errors.append(f"{path}: must be an object")
        return

    _check_str(ch.get("name"), f"{path}.name", errors)
    ch_type = ch.get("type", "text")
    if ch_type not in VALID_CHANNEL_TYPES:
        errors.append(f"{path}.type: must be 'text' or 'voice', got {ch_type!r}")

    slowmode = ch.get("slowmode", 0)
    if not isinstance(slowmode, int) or isinstance(slowmode, bool) or slowmode < 0:
        errors.append(f"{path}.slowmode: must be a non-negative integer")

    for field in ("visible_to", "hidden_from"):
        lst = ch.get(field, [])
        if not isinstance(lst, list):
            errors.append(f"{path}.{field}: must be a list")
        else:
            for r in lst:
                if r not in role_names:
                    errors.append(
                        f"{path}.{field}: role {r!r} not found in top-level roles list"
                    )


def _validate_category(cat: Any, idx: int, role_names: set, errors: List[str]) -> None:
    path = f"categories[{idx}]"
    if not isinstance(cat, dict):
        errors.append(f"{path}: must be an object")
        return

    if not _check_str(cat.get("name"), f"{path}.name", errors):
        return

    cat_name = cat["name"]
    visible_to = cat.get("visible_to", [])
    if not isinstance(visible_to, list):
        errors.append(f"{path}.visible_to: must be a list")
    else:
        for r in visible_to:
            if r not in role_names:
                errors.append(f"{path}.visible_to: role {r!r} not defined in roles")

    channels = cat.get("channels", [])
    if not isinstance(channels, list):
        errors.append(f"{path}.channels: must be a list")
    else:
        for i, ch in enumerate(channels):
            _validate_channel(ch, i, cat_name, role_names, errors)


def _validate_role(role: Any, idx: int, errors: List[str]) -> None:
    path = f"roles[{idx}]"
    if not isinstance(role, dict):
        errors.append(f"{path}: must be an object")
        return

    _check_str(role.get("name"), f"{path}.name", errors)

    color = role.get("color", "#000000")
    if not isinstance(color, str) or not color.startswith("#") or len(color) not in (4, 7):
        errors.append(f"{path}.color: must be a hex color like '#FF5733'")

    for bool_field in ("hoist", "mentionable"):
        if bool_field in role:
            _check_bool(role[bool_field], f"{path}.{bool_field}", errors)

    perms = role.get("permissions", [])
    if not isinstance(perms, list):
        errors.append(f"{path}.permissions: must be a list")
    else:
        for p in perms:
            if p not in VALID_PERMISSIONS:
                errors.append(f"{path}.permissions: unknown permission {p!r}")


def validate(blueprint: Any) -> Tuple[bool, List[str]]:
    """
    Validates a blueprint dict. Returns (True, []) on success or
    (False, [error, ...]) on failure.
    """
    errors: List[str] = []

    if not isinstance(blueprint, dict):
        return False, ["Blueprint must be a JSON object"]

    _check_str(blueprint.get("server_name"), "server_name", errors)

    roles = blueprint.get("roles", [])
    if not isinstance(roles, list):
        errors.append("roles: must be a list")
        role_names: set = set()
    else:
        role_names = set()
        for i, role in enumerate(roles):
            _validate_role(role, i, errors)
            if isinstance(role, dict) and isinstance(role.get("name"), str):
                role_names.add(role["name"])

    categories = blueprint.get("categories", [])
    if not isinstance(categories, list):
        errors.append("categories: must be a list")
    elif not categories:
        errors.append("categories: must contain at least one category")
    else:
        for i, cat in enumerate(categories):
            _validate_category(cat, i, role_names, errors)

    return len(errors) == 0, errors


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
