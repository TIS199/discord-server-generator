import re
with open('/home/tis/Projects/discord-server-generator/src/commands.py', 'r') as f:
    content = f.read()

# Replace the /build command definition
build_pattern = r'# ── /build ───────────────────────────────────────────────────────────.*?# ── /reset ───────────────────────────────────────────────────────────'

new_build = """# ── /build ───────────────────────────────────────────────────────────
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
                    f"❌ I'm not in a guild with ID `{guild_id_int}`, or that ID is wrong.\\n"
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
                    f"❌ Failed to parse JSON file: `{exc}`\\nPlease check the file from your local AI.",
                    ephemeral=True,
                )
                return

            # Validate blueprint
            is_valid, errors = validate(blueprint)
            if not is_valid:
                error_list = "\\n".join(f"• {e}" for e in errors[:20])
                await interaction.followup.send(
                    f"❌ Blueprint validation failed:\\n{error_list}",
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
                    f"**Target Guild:** {target_guild.name} (`{target_guild.id}`)\\n\\n"
                    f"**Server Name:** {server_name}\\n"
                    f"**Description:** {server_desc or '—'}\\n\\n"
                    f"**Roles:** {num_roles}\\n"
                    f"**Categories:** {num_cats}\\n"
                    f"**Channels:** {num_channels}\\n"
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
                summary = summary[:1900] + "\\n…(truncated)"

            status_emoji = "✅" if success else "⚠️"
            try:
                await resp_interaction.followup.send(
                    f"{status_emoji} **Build complete for {server_name}**\\n\\n{summary}",
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

        # ── /reset ───────────────────────────────────────────────────────────"""

content = re.sub(build_pattern, new_build, content, flags=re.DOTALL)
content = content.replace("from src.views import BlueprintModal, BuildConfirmView", "from src.views import BuildConfirmView")

with open('/home/tis/Projects/discord-server-generator/src/commands.py', 'w') as f:
    f.write(content)

