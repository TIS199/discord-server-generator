# Discord Server Generator 🏗️

A Discord bot that builds entire servers from a plain-English prompt — powered by **your local AI** (Ollama, LM Studio, etc.). No cloud AI API key required.

## How It Works

```
/create "make a gaming server for Minecraft"
         │
    Bot outputs a structured prompt (copy it)
         │
  Paste into local AI → get JSON blueprint
         │
    /build <guild_id>  (paste the JSON)
         │
  Bot validates → shows preview → you approve
         │
    Channels, categories & roles are created ✅
```

## Commands

| Command | Description |
|---|---|
| `/create <prompt>` | Generates the instruction-set text to paste into your local AI |
| `/build <guild_id>` | Opens a modal — paste the AI's JSON; bot builds the server |
| `/reset` | Clears your session |

## Setup

### 1. Clone & install

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
# Edit .env and set DISCORD_BOT_TOKEN
```

### 3. Run locally

```bash
python bot.py
```

---

## GitHub Actions

### Run manually (up to 6 hours)

1. Go to **Actions → Run Bot (Manual)** → **Run workflow**
2. Add `DISCORD_BOT_TOKEN` to **Settings → Secrets → Actions**

### Deploy to VPS on push to `main`

Required secrets:

| Secret | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Your bot token |
| `BOT_ALLOWED_ROLES` | Comma-separated role names |
| `SSH_HOST` | VPS IP or hostname |
| `SSH_USER` | SSH username |
| `SSH_PRIVATE_KEY` | Private key (no passphrase) |
| `SSH_PORT` | SSH port (default 22) |
| `LOG_WEBHOOK_URL` | Optional Discord webhook |

### systemd service (VPS production setup)

Create `/etc/systemd/system/discord-server-generator.service`:

```ini
[Unit]
Description=Discord Server Generator Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/discord-server-generator
ExecStart=/home/YOUR_USER/discord-server-generator/.venv/bin/python bot.py
Restart=on-failure
RestartSec=10
EnvironmentFile=/home/YOUR_USER/discord-server-generator/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable discord-server-generator
sudo systemctl start discord-server-generator
sudo systemctl status discord-server-generator
```

---

## Blueprint JSON Schema

Your local AI must return a JSON object matching this structure:

```json
{
  "server_name": "My Server",
  "server_description": "A short description",
  "roles": [
    {
      "name": "admin",
      "color": "#E74C3C",
      "hoist": true,
      "mentionable": true,
      "permissions": ["administrator"]
    }
  ],
  "categories": [
    {
      "name": "general",
      "visible_to": [],
      "channels": [
        {
          "name": "general-chat",
          "type": "text",
          "topic": "Talk about anything",
          "slowmode": 0,
          "nsfw": false,
          "visible_to": [],
          "hidden_from": []
        },
        {
          "name": "lobby",
          "type": "voice"
        }
      ]
    }
  ]
}
```

### Valid permissions

`view_channel`, `send_messages`, `read_message_history`, `manage_messages`,
`manage_channels`, `manage_roles`, `kick_members`, `ban_members`, `administrator`,
`embed_links`, `attach_files`, `add_reactions`, `use_external_emojis`,
`connect`, `speak`, `mute_members`, `deafen_members`, `move_members`, `use_voice_activation`

---

## Bot Permissions Required

When adding the bot to a server, grant:
- Manage Channels
- Manage Roles
- View Channels
- Send Messages

---

## License

Copyright (c) 2025 TIS199 — Educational and Testing Use Only.
