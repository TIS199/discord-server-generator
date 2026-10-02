"""Build the local-AI instruction set for a Discord server blueprint."""

import json

from src.validator import VALID_PERMISSIONS


_PERMISSION_NAMES = ", ".join(sorted(VALID_PERMISSIONS))

BLUEPRINT_SCHEMA = {
    "server_name": "string — proposed name shown in the preview",
    "server_description": "string — short description shown in the preview",
    "guild_settings": {
        "name": "string (optional) — change the target server name",
        "description": "string (optional) — change the target server description",
        "verification_level": "none | low | medium | high | highest",
        "default_notifications": "all_messages | only_mentions",
        "explicit_content_filter": "disabled | no_role | all_members",
        "afk_timeout": "60 | 300 | 900 | 1800 | 3600 seconds",
        "preferred_locale": "Discord locale code, for example en-US",
        "premium_progress_bar_enabled": "boolean",
    },
    "roles": [
        {
            "name": "string — create this role, or configure the matching existing role",
            "color": "hex string such as #FF5733 (optional; an existing role keeps its color if omitted)",
            "hoist": "boolean (optional; an existing role keeps its setting if omitted)",
            "mentionable": "boolean (optional; an existing role keeps its setting if omitted)",
            "update_existing": "boolean (optional, default true)",
            "permissions": f"optional list of Discord role permissions — any of: {_PERMISSION_NAMES}; omitted existing roles keep their permissions",
        }
    ],
    "categories": [
        {
            "name": "string",
            "visible_to": ["legacy shorthand: roles that can see this category; empty means everyone"],
            "permission_overwrites": {
                "Role Name or @everyone": {
                    "view_channel": "true to allow, false to deny, null to inherit",
                    "send_messages": "true | false | null",
                }
            },
            "channels": [
                {
                    "name": "string",
                    "type": "text | announcement | voice | stage | forum",
                    "topic": "string (optional; used by text, announcement, and forum channels)",
                    "slowmode": "integer seconds (optional, 0–21600; text, announcement, and forum only)",
                    "nsfw": "boolean (optional)",
                    "bitrate": "integer bps (optional; voice and stage channels only)",
                    "user_limit": "integer 0–99 (optional; voice and stage channels only)",
                    "default_auto_archive_duration": "60 | 1440 | 4320 | 10080 minutes (optional; text, announcement, and forum only)",
                    "default_thread_slowmode_delay": "integer seconds 0–21600 (optional; text, announcement, and forum only)",
                    "visible_to": ["legacy shorthand: roles that can see this channel"],
                    "hidden_from": ["legacy shorthand: roles denied access to this channel"],
                    "permission_overwrites": {
                        "Role Name or @everyone": {
                            "view_channel": "true to allow, false to deny, null to inherit",
                            "send_messages": "true | false | null",
                        }
                    },
                }
            ],
        }
    ],
    "messages": [
        {
            "channel": "channel name (or category/channel to disambiguate)",
            "category": "category name (optional alternative for disambiguation)",
            "content": "string (optional if an embed is present)",
            "embed": {
                "title": "string",
                "description": "string",
                "url": "https://example.com (optional)",
                "color": "#5865F2 (optional)",
                "author": {"name": "string", "url": "https://example.com", "icon_url": "https://..."},
                "footer": {"text": "string", "icon_url": "https://..."},
                "thumbnail_url": "https://...",
                "image_url": "https://...",
                "fields": [{"name": "string", "value": "string", "inline": False}],
                "timestamp": "ISO 8601 date-time (optional)",
            },
            "embeds": ["optional list of up to 10 embed objects using the same fields"],
            "reactions": ["optional list of up to 20 distinct emoji strings the bot adds to its first sent message; Unicode emoji or custom emoji markup such as <:name:id>"],
            "use_webhook": "boolean (optional, default false)",
            "webhook_name": "string (optional)",
            "webhook_avatar_url": "https://... (optional)",
        }
    ],
}

_RULES = """
RULES — FOLLOW EVERY RULE:
1. Generate one complete, valid JSON blueprint as the default deliverable.
2. If you can create files, save the JSON as server-blueprint.json. If you cannot create
   files, return the raw JSON so the user can save it with that filename.
3. Output only the JSON object: no markdown fences, comments, explanations, or extra text.
4. The JSON must be valid and parseable by Python's json.loads(). Use double-quoted strings.
5. Omit optional fields you do not need. Do not invent permissions or permission names.
6. Role names in permission_overwrites must match a role in this blueprint or a role that
   already exists in the target server. Use @everyone for the default role.
7. In permission_overwrites, true allows a permission, false denies it, and null inherits it.
   Configure only the permissions that need an explicit allow or deny.
8. Use permission_overwrites for detailed role access at category or channel level. Channel
   overrides inherit category rules unless the channel specifies a different value.
9. Role permissions are the permissions granted to that role. Keep them minimal and never
   grant administrator unless the user explicitly asks for an administrator role.
10. The builder updates same-named categories and channels, plus same-named roles unless
    update_existing is false. Use unique names and do not create duplicate categories or channels.
11. Use lowercase channel/category names with hyphens instead of spaces.
12. Do not include @everyone in the roles array; Discord manages it automatically.
13. Messages may contain plain text, an embed, or both. Use concise embeds and HTTPS image URLs.
14. A message may include up to 20 distinct emoji strings in reactions; the bot adds these to
    the first message it sends for that entry. Use Unicode emoji or custom emoji markup such as
    <:name:id>; custom emoji must be available to the bot in the target server.
15. Do not include secrets, bot tokens, or private data in the blueprint.
""".strip()

_EXAMPLE = {
    "server_name": "Pixel Squad",
    "server_description": "A chill gaming community",
    "guild_settings": {
        "verification_level": "low",
        "default_notifications": "only_mentions",
        "explicit_content_filter": "all_members",
    },
    "roles": [
        {
            "name": "Member",
            "color": "#3498DB",
            "hoist": False,
            "mentionable": False,
            "permissions": ["view_channel", "send_messages", "read_message_history", "embed_links"],
        },
        {
            "name": "Moderator",
            "color": "#E67E22",
            "hoist": True,
            "mentionable": True,
            "permissions": ["view_channel", "send_messages", "read_message_history", "manage_messages"],
        },
    ],
    "categories": [
        {
            "name": "information",
            "permission_overwrites": {
                "@everyone": {"send_messages": False},
                "Member": {"view_channel": True, "read_message_history": True},
            },
            "channels": [
                {"name": "welcome", "type": "text", "topic": "Start here"},
                {"name": "rules", "type": "announcement"},
            ],
        },
        {
            "name": "community",
            "permission_overwrites": {
                "@everyone": {"view_channel": False},
                "Member": {"view_channel": True},
            },
            "channels": [
                {"name": "general-chat", "type": "text"},
                {"name": "voice-lounge", "type": "voice", "user_limit": 0},
                {"name": "introductions", "type": "forum", "topic": "Say hello to the community"},
            ],
        },
    ],
    "messages": [
        {
            "channel": "rules",
            "content": "Please read and follow these guidelines.",
            "reactions": ["📜", "✅"],
            "embed": {
                "title": "Welcome to Pixel Squad",
                "description": "Be kind, stay on topic, and have fun.",
                "color": "#5865F2",
                "fields": [
                    {"name": "Be respectful", "value": "Treat every member with respect.", "inline": False},
                    {"name": "Need help?", "value": "Ask a moderator in the help channel.", "inline": False},
                ],
                "footer": {"text": "Pixel Squad community guidelines"},
            },
        }
    ],
}


def build_prompt(user_request: str) -> str:
    """Return a complete instruction set for a local AI model."""
    schema_str = json.dumps(BLUEPRINT_SCHEMA, indent=2, ensure_ascii=False)
    example_str = json.dumps(_EXAMPLE, indent=2, ensure_ascii=False)
    prompt = f"""=== DISCORD SERVER GENERATOR — LOCAL AI INSTRUCTIONS ===

You are a Discord server architect. Design a complete, practical server from the
user request below. Your default deliverable is a JSON blueprint file named
server-blueprint.json. Follow the output schema and rules exactly.

--- OUTPUT SCHEMA ---
{schema_str}

--- EXAMPLE OUTPUT ---
{example_str}

--- {_RULES} ---

--- USER REQUEST ---
{user_request}

Now generate the JSON blueprint. Return raw JSON only; when file creation is available,
save that JSON as server-blueprint.json.
"""
    return prompt.strip()


# Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
