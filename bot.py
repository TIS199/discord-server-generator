"""
bot.py — Entry point for the Discord Server Generator bot.

Usage:
    python bot.py

Environment variables (set in .env or GitHub Secrets):
    DISCORD_BOT_TOKEN   — required
    BOT_ALLOWED_ROLES   — comma-separated role names (default: Administrator,Moderator)
    LOG_WEBHOOK_URL     — optional Discord webhook for structured logs
    RATE_LIMIT_SECONDS  — optional, default 10
"""

import asyncio
import sys

import discord

import config
from src.commands import CommandCore
from src.logger import logger


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
command_core: CommandCore | None = None


@bot.event
async def on_ready() -> None:
    global command_core
    if bot.user:
        logger.info(f"✅ Logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"📊 Connected to {len(bot.guilds)} guild(s)")

    command_core = CommandCore(bot)
    await command_core.sync_commands()

    logger.info("🚀 Discord Server Generator is ready!")
    logger.info("   /create <prompt>  — generate local-AI instruction set")
    logger.info("   /build  <guild_id> — paste blueprint JSON and build")
    logger.info("   /reset             — clear session")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    logger.info(f"➕ Joined guild: {guild.name} (ID: {guild.id})")
    if command_core:
        await command_core.sync_commands(guild.id)


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    logger.info(f"➖ Removed from guild: {guild.name} (ID: {guild.id})")


@bot.event
async def on_error(event: str, *args, **kwargs) -> None:
    logger.error(f"Error in event '{event}': {sys.exc_info()}")


async def main() -> None:
    if not config.DISCORD_BOT_TOKEN:
        logger.error("❌ DISCORD_BOT_TOKEN is not set. Add it to .env or GitHub Secrets.")
        sys.exit(1)

    logger.info("🤖 Starting Discord Server Generator…")
    logger.info(f"🔐 Allowed roles: {', '.join(config.BOT_ALLOWED_ROLES)}")

    try:
        await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown requested")
        await bot.close()
    except discord.LoginFailure:
        logger.error("❌ Invalid DISCORD_BOT_TOKEN — check your credentials.")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"❌ Fatal error: {exc}")
        await bot.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
