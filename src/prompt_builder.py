"""
prompt_builder.py
-----------------
Generates the instruction-set text block that the user pastes into their
local AI (Ollama, LM Studio, etc.). The local AI must return a JSON
blueprint that matches the schema defined here.
"""

import json

# ── Blueprint schema the local AI must follow ───────────────────────────────
BLUEPRINT_SCHEMA = {
    "server_name": "string — name for the server",
    "server_description": "string — short description",
    "roles": [
        {
            "name": "string",
            "color": "hex string e.g. #FF5733 (optional, default #000000)",
            "hoist": "bool — show separately in member list (optional, default false)",
            "mentionable": "bool (optional, default false)",
            "permissions": [
                "list of permission names — choose from: view_channel, send_messages, "
                "read_message_history, manage_messages, manage_channels, manage_roles, "
                "kick_members, ban_members, administrator, embed_links, attach_files, "
                "add_reactions, use_external_emojis, connect, speak, mute_members, "
                "deafen_members, move_members, use_voice_activation"
            ],
        }
    ],
    "categories": [
        {
            "name": "string",
            "visible_to": ["list of role names that can see this category (empty = everyone)"],
            "channels": [
                {
                    "name": "string",
                    "type": "text | voice",
                    "topic": "string (text channels only, optional)",
                    "slowmode": "int seconds (optional, default 0)",
                    "nsfw": "bool (optional, default false)",
                    "visible_to": ["role names that can see this channel (overrides category if set)"],
                    "hidden_from": ["role names that cannot see this channel"],
                }
            ],
        }
    ],
    "messages": [
        {
            "channel": "string — name of the channel to send the message in",
            "content": "string — the message text to send",
            "use_webhook": "bool (optional, default false) — use a webhook to send the message",
            "webhook_name": "string (optional) — name of the webhook/bot if use_webhook is true",
            "webhook_avatar_url": "string (optional) — URL to image for webhook avatar"
        }
    ]
}

_RULES = """
RULES — YOU MUST FOLLOW ALL OF THESE:
1. Output ONLY a single raw JSON object. No markdown fences, no explanations, no extra text.
2. The JSON must be valid and parseable by Python's json.loads().
3. Every field marked as optional may be omitted; the bot will use the default.
4. Role names used in visible_to / hidden_from must exactly match names defined in "roles".
5. Channel and category names must be lowercase, use hyphens instead of spaces (e.g. "general-chat").
6. Keep role permission lists minimal — only include what the role actually needs.
7. Do NOT include @everyone in the roles array; it is handled automatically.
""".strip()

_EXAMPLE = {
    "server_name": "Pixel Squad",
    "server_description": "A chill gaming community",
    "roles": [
        {"name": "admin", "color": "#E74C3C", "hoist": True, "mentionable": True,
         "permissions": ["administrator"]},
        {"name": "member", "color": "#3498DB", "hoist": False,
         "permissions": ["view_channel", "send_messages", "read_message_history",
                         "embed_links", "attach_files", "add_reactions"]},
    ],
    "categories": [
        {
            "name": "information",
            "visible_to": [],
            "channels": [
                {"name": "welcome", "type": "text", "topic": "Welcome to Pixel Squad!"},
                {"name": "rules", "type": "text"},
                {"name": "announcements", "type": "text"},
            ],
        },
        {
            "name": "general",
            "visible_to": ["member", "admin"],
            "channels": [
                {"name": "general-chat", "type": "text", "topic": "Talk about anything"},
                {"name": "media", "type": "text"},
                {"name": "lobby", "type": "voice"},
            ],
        },
        {
            "name": "admin-only",
            "visible_to": ["admin"],
            "channels": [
                {"name": "admin-chat", "type": "text"},
                {"name": "logs", "type": "text"},
            ],
        },
    ],
    "messages": [
        {
            "channel": "rules",
            "content": "Welcome to Pixel Squad! Please follow all rules.",
            "use_webhook": True,
            "webhook_name": "Server Guide",
            "webhook_avatar_url": "https://i.imgur.com/example.png"
        }
    ]
}


def build_prompt(user_request: str) -> str:
    """
    Returns the full instruction-set string the user copies into their
    local AI model.
    """
    schema_str = json.dumps(BLUEPRINT_SCHEMA, indent=2)
    example_str = json.dumps(_EXAMPLE, indent=2)

    prompt = f"""=== DISCORD SERVER GENERATOR — LOCAL AI INSTRUCTIONS ===

You are a Discord server architect. Your job is to design a complete Discord server
based on the user's request below, and output a single JSON blueprint.

--- OUTPUT SCHEMA ---
{schema_str}

--- EXAMPLE OUTPUT ---
{example_str}

--- {_RULES} ---

--- USER REQUEST ---
{user_request}

Now output the JSON blueprint for this server. Remember: raw JSON only, no markdown.
"""
    return prompt.strip()


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
