with open('/home/tis/Projects/discord-server-generator/src/prompt_builder.py', 'r') as f:
    content = f.read()

schema_replace = """                    "hidden_from": ["role names that cannot see this channel"],
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
}"""

example_replace = """        },
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
}"""

content = content.replace("""                    "hidden_from": ["role names that cannot see this channel"],
                }
            ],
        }
    ],
}""", schema_replace)

content = content.replace("""        },
    ],
}""", example_replace)

with open('/home/tis/Projects/discord-server-generator/src/prompt_builder.py', 'w') as f:
    f.write(content)
