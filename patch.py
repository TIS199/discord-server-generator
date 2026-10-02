import sys

with open('/home/tis/Projects/discord-server-generator/src/builder.py', 'r') as f:
    content = f.read()

replacement = """            # Small delay to avoid hitting Discord rate limits
            await asyncio.sleep(0.4)

    # ── 3. Process messages & webhooks ──────────────────────────────────────
    messages_def = blueprint.get("messages", [])
    if messages_def:
        msg_results = await process_messages(guild, messages_def)
        for msg_res in msg_results:
            if msg_res.startswith("  ✅"):
                result.ok(msg_res[4:].strip())
            else:
                result.fail(msg_res[4:].strip(), "Webhook/Message failed")

    return result.success, result.summary()"""

content = content.replace("""            # Small delay to avoid hitting Discord rate limits
            await asyncio.sleep(0.4)

    return result.success, result.summary()""", replacement)

with open('/home/tis/Projects/discord-server-generator/src/builder.py', 'w') as f:
    f.write(content)

