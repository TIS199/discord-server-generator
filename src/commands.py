"""
commands.py
-----------
Registers and handles the three slash commands:
  /create <prompt>      — generate local-AI instruction set
  /build  <guild_id>    — paste JSON blueprint and build the server
  /reset                — clear any in-progress session (currently no-op)
"""

import json
import time
from typing import Dict, Optional

import discord
from discord import app_commands

import config
from src.logger import logger, log_action, log_error
from src.prompt_builder import build_prompt
from src.validator import validate
from src.builder import build_server
from src.views import BuildConfirmView


class CommandCore:
    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self.tree = app_commands.CommandTree(bot)
        self._rate_limiter: Dict[int, float] = {}
        self._register_commands()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _check_permissions(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not hasattr(interaction.user, "roles"):
            return False
        return any(
            role.name in config.BOT_ALLOWED_ROLES
            for role in interaction.user.roles  # type: ignore[union-attr]
        )

    def _check_rate_limit(self, user_id: int) -> Optional[int]:
        """Returns seconds to wait, or None if not rate-limited."""
        now = time.time()
        last = self._rate_limiter.get(user_id)
        if last and (now - last) < config.RATE_LIMIT_SECONDS:
            return int(config.RATE_LIMIT_SECONDS - (now - last))
        self._rate_limiter[user_id] = now
        return None

    # ── Command registration ─────────────────────────────────────────────────

    def _register_commands(self) -> None:

        # ── /create ──────────────────────────────────────────────────────────
        @self.tree.command(
            name="create",
            description="Generate the local-AI instruction set for a new server",
        )
        @app_commands.describe(prompt="Describe the server you want to create")
        async def create_cmd(interaction: discord.Interaction, prompt: str) -> None:
            if not self._check_permissions(interaction):
                await interaction.response.send_message(
                    f"❌ You need one of these roles: {', '.join(config.BOT_ALLOWED_ROLES)}",
                    ephemeral=True,
                )
                return

            wait = self._check_rate_limit(interaction.user.id)
            if wait:
                await interaction.response.send_message(
                    f"⏳ Please wait {wait}s before using this command again.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)

            instruction_set = build_prompt(prompt)

            # Split into chunks if over Discord's 2000-char message limit
            chunks = [instruction_set[i:i+1900] for i in range(0, len(instruction_set), 1900)]

            await interaction.followup.send(
                "📋 **Instruction set generated!**\n"
                "Copy the text below and paste it into your local AI (Ollama, LM Studio, etc.).\n"
                "Then use `/build <guild_id>` to upload the AI's JSON output back here.",
                ephemeral=True,
            )

            for chunk in chunks:
                await interaction.followup.send(f"```\n{chunk}\n```", ephemeral=True)

            guild_name = interaction.guild.name if interaction.guild else "Unknown"
            await log_action(str(interaction.user), guild_name, "PromptGenerated", prompt[:200])

        # ── /build ───────────────────────────────────────────────────────────
        @self.tree.command(
            name="build",
            description="Upload the AI's JSON blueprint file to build a server",
        )
        @app_commands.describe(
            guild_id="The ID of the target guild to build in",
            blueprint_file="The JSON file output by the local AI"
        )
        async def build_cmd(interaction: discord.Interaction, guild_id: str, blueprint_file: discord.Attachment) -> None:
            if not self._check_permissions(interaction):
                await interaction.response.send_message(
                    f"❌ You need one of these roles: {', '.join(config.BOT_ALLOWED_ROLES)}",
                    ephemeral=True,
                )
                return

            wait = self._check_rate_limit(interaction.user.id)
            if wait:
                await interaction.response.send_message(
                    f"⏳ Please wait {wait}s before using this command again.",
                    ephemeral=True,
                )
                return

            # Validate guild_id format
            try:
                guild_id_int = int(guild_id)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid guild ID — must be a number (e.g. `1234567890`).",
                    ephemeral=True,
                )
                return

            # Look up the target guild
            target_guild = self.bot.get_guild(guild_id_int)
            if target_guild is None:
                await interaction.response.send_message(
                    f"❌ I'm not in a guild with ID `{guild_id_int}`, or that ID is wrong.\n"
                    "Make sure the bot has been added to that server.",
                    ephemeral=True,
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=True)

            if not blueprint_file.filename.endswith('.json'):
                await interaction.followup.send("❌ Please upload a .json file.", ephemeral=True)
                return
            
            try:
                raw_bytes = await blueprint_file.read()
                raw_json = raw_bytes.decode('utf-8')
                blueprint = json.loads(raw_json)
            except Exception as exc:
                await interaction.followup.send(
                    f"❌ Failed to parse JSON file: `{exc}`\nPlease check the file from your local AI.",
                    ephemeral=True,
                )
                return

            # Validate blueprint
            is_valid, errors = validate(blueprint)
            if not is_valid:
                error_list = "\n".join(f"• {e}" for e in errors[:20])
                await interaction.followup.send(
                    f"❌ Blueprint validation failed:\n{error_list}",
                    ephemeral=True,
                )
                return

            # Show preview embed
            server_name = blueprint.get("server_name", "(unnamed)")
            server_desc = blueprint.get("server_description", "")
            num_roles = len(blueprint.get("roles", []))
            num_cats = len(blueprint.get("categories", []))
            num_channels = sum(
                len(c.get("channels", []))
                for c in blueprint.get("categories", [])
            )
            num_msgs = len(blueprint.get("messages", []))

            embed = discord.Embed(
                title="🏗️ Server Blueprint Preview",
                description=(
                    f"**Target Guild:** {target_guild.name} (`{target_guild.id}`)\n\n"
                    f"**Server Name:** {server_name}\n"
                    f"**Description:** {server_desc or '—'}\n\n"
                    f"**Roles:** {num_roles}\n"
                    f"**Categories:** {num_cats}\n"
                    f"**Channels:** {num_channels}\n"
                    f"**Messages:** {num_msgs}"
                ),
                color=discord.Color.blurple(),
            )
            embed.set_footer(text="Click ✅ Approve to build or ❌ Cancel to abort.")

            view = BuildConfirmView(owner_id=interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

            await view.wait()

            if view.value is None:
                await interaction.followup.send(
                    "⏰ Confirmation timed out. Please run `/build` again.", ephemeral=True
                )
                return

            if not view.value:
                # User clicked Cancel
                return

            # ── Build ─────────────────────────────────────────────────────
            resp_interaction = view.response_interaction or interaction
            try:
                await resp_interaction.followup.send(
                    f"⚙️ Building **{server_name}** in **{target_guild.name}**…",
                    ephemeral=True,
                )
            except Exception:
                pass

            success, summary = await build_server(target_guild, blueprint)

            # Truncate summary for Discord's 2000-char limit
            if len(summary) > 1900:
                summary = summary[:1900] + "\n…(truncated)"

            status_emoji = "✅" if success else "⚠️"
            try:
                await resp_interaction.followup.send(
                    f"{status_emoji} **Build complete for {server_name}**\n\n{summary}",
                    ephemeral=True,
                )
            except Exception:
                pass

            guild_name = interaction.guild.name if interaction.guild else "Unknown"
            if success:
                await log_action(
                    str(interaction.user), guild_name,
                    "ServerBuilt", f"Built '{server_name}' in guild {target_guild.id}"
                )
            else:
                await log_error(
                    str(interaction.user), guild_name,
                    "BuildPartialFailure", summary[:500]
                )

        # ── /reset ───────────────────────────────────────────────────────────
        @self.tree.command(name="reset", description="Clear your current session")
        async def reset_cmd(interaction: discord.Interaction) -> None:
            if not self._check_permissions(interaction):
                await interaction.response.send_message(
                    f"❌ You need one of these roles: {', '.join(config.BOT_ALLOWED_ROLES)}",
                    ephemeral=True,
                )
                return
            # No persistent state to clear in this bot, but kept for UX consistency
            await interaction.response.send_message(
                "✅ Session reset. You can start fresh with `/create`.", ephemeral=True
            )

    async def sync_commands(self, guild_id: Optional[int] = None) -> None:
        if guild_id:
            guild_obj = discord.Object(id=guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            logger.info(f"Commands synced to guild {guild_id}")
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
