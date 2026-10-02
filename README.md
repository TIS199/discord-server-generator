# Discord Server Generator

A Discord bot that applies a JSON server blueprint generated from a plain-language request. The blueprint can be created by a local AI such as Ollama or LM Studio; no cloud AI API key is required.

## How it works

1. Run `/create` with a description of the server. The bot returns a text file of instructions for your local AI.
2. The instructions ask the AI to create `server-blueprint.json`. If the AI cannot write files, it returns raw JSON for you to save with that name.
3. Upload that file with `/build`, choose the target server, review the preview, and approve it.
4. The bot applies guild settings, roles, categories, channels, permission overwrites, and starter messages.

## Commands

| Command | Description |
|---|---|
| `/create <prompt>` | Generate local-AI instructions and download them as a text file. |
| `/build <guild_id> <blueprint_file>` | Validate, preview, and apply a JSON blueprint. The caller must be an owner or authorized server manager in the target server. |
| `/nuke <confirmation>` | Clear server structure after typing `NUKE <server-id>` and approving a second confirmation button. Owner or Administrator only. |
| `/reset` | Clear the current interaction session. |

`/nuke` deletes channels and their message history, removable roles, custom emoji, stickers, and scheduled events. It retains members, the server itself, Discord's `@everyone` role, managed roles, and roles above the bot's highest role. The preview reports bot permission or role-hierarchy limits before confirmation.

## Blueprint features

- Create roles or configure existing roles by name, including color, hoisting, mentionability, and any permission supported by the installed discord.py version. Existing roles update by default; set `update_existing` to `false` to leave one untouched. Omitted optional role settings are preserved.
- Apply the same blueprint again to update matching categories and channels instead of creating duplicates. Omitted optional channel settings are preserved.
- Configure guild name and description, verification level, default notifications, content filter, AFK timeout, locale, and premium progress bar.
- Create text, announcement, voice, stage, and forum channels.
- Set category-level or channel-level allow/deny rules for any configured or existing role. `true` allows a permission, `false` denies it, and `null` inherits the parent/default value. Channel rules start with the category rules and then apply channel changes.
- Send plain text, rich embeds, or both. Embed features include title, description, color, author, footer, images, thumbnails, fields, URLs, and timestamps. Add up to 20 Unicode or custom emoji reactions to the first message sent for each message entry.
- Disambiguate duplicate text channel names with `"category": "news"` or `"channel": "news/announcements"` in a message definition.

## Example blueprint

```json
{
  "server_name": "Pixel Squad",
  "server_description": "A friendly gaming community",
  "guild_settings": {
    "verification_level": "low",
    "default_notifications": "only_mentions",
    "explicit_content_filter": "all_members"
  },
  "roles": [
    {
      "name": "Member",
      "color": "#3498DB",
      "hoist": false,
      "mentionable": false,
      "permissions": [
        "view_channel",
        "send_messages",
        "read_message_history",
        "embed_links"
      ]
    },
    {
      "name": "Moderator",
      "color": "#E67E22",
      "hoist": true,
      "mentionable": true,
      "permissions": [
        "view_channel",
        "send_messages",
        "read_message_history",
        "manage_messages"
      ]
    }
  ],
  "categories": [
    {
      "name": "information",
      "permission_overwrites": {
        "@everyone": {"send_messages": false},
        "Member": {"view_channel": true, "read_message_history": true}
      },
      "channels": [
        {"name": "welcome", "type": "text", "topic": "Start here"},
        {"name": "rules", "type": "announcement"}
      ]
    },
    {
      "name": "community",
      "permission_overwrites": {
        "@everyone": {"view_channel": false},
        "Member": {"view_channel": true}
      },
      "channels": [
        {"name": "general-chat", "type": "text"},
        {"name": "voice-lounge", "type": "voice", "user_limit": 0},
        {"name": "introductions", "type": "forum", "topic": "Say hello"}
      ]
    }
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
          {"name": "Be respectful", "value": "Treat every member with respect."},
          {"name": "Need help?", "value": "Ask a moderator in the help channel."}
        ],
        "footer": {"text": "Pixel Squad community guidelines"}
      }
    }
  ]
}
```

For a channel-specific exception, place its rules under that channel:

```json
{
  "name": "mod-chat",
  "type": "text",
  "permission_overwrites": {
    "@everyone": {"view_channel": false},
    "Moderator": {"view_channel": true, "send_messages": true},
    "Member": {"send_messages": false}
  }
}
```

The bot checks that overwrite role names exist either in the blueprint or in the target server. The full supported permission list is supplied in each `/create` instruction set.

## Setup

### 1. Install

```bash
git clone https://github.com/TIS199/discord-server-generator
cd discord-server-generator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Set DISCORD_BOT_TOKEN in .env
```

Invite the bot with the `bot` and `applications.commands` scopes. Enable the Server Members intent in the Discord Developer Portal. Grant the bot:

- Manage Channels and Manage Roles
- Manage Server for applying optional guild settings
- View Channels, Send Messages, Embed Links, and Read Message History
- Add Reactions (for blueprint messages with `reactions`)
- Manage Webhooks if blueprints use `use_webhook: true`
- Manage Events and Manage Expressions if `/nuke` should remove events, emoji, and stickers
- Use Application Commands

The bot's highest role must be above roles it needs to update or remove. Discord may reject channel types or guild settings that require server features the target guild has not enabled.

### 3. Run

```bash
python bot.py
```

## Configuration

| Variable | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Required bot token. |
| `BOT_ALLOWED_ROLES` | Comma-separated role names for `/create` and `/reset`; defaults to `Administrator,Moderator`. Server managers and owners can also use those commands. |
| `RATE_LIMIT_SECONDS` | Per-user command rate limit; defaults to 10. |
| `LOG_WEBHOOK_URL` | Optional webhook for structured action logs. |

## GitHub Actions and VPS deployment

The repository includes a manual GitHub Actions workflow for running the bot and a push-to-`main` deployment workflow for a VPS. Configure the corresponding repository secrets (`DISCORD_BOT_TOKEN`, `BOT_ALLOWED_ROLES`, `LOG_WEBHOOK_URL`, and the SSH credentials listed in the deployment workflow) before using them.

For a long-running VPS installation, run `bot.py` as a systemd service and keep the token in a protected environment file.

## License

Copyright (c) 2025 TIS199 — Educational and Testing Use Only. Redistribution or commercial use is strictly prohibited.
