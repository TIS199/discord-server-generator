"""
views.py
--------
Discord UI components: modal for pasting JSON blueprint and
confirmation buttons for approving or cancelling a build.
"""

import asyncio
import discord
from typing import Optional


class BlueprintModal(discord.ui.Modal, title="Paste AI Blueprint JSON"):
    """Text input modal where the user pastes the local AI's JSON output."""

    blueprint_input = discord.ui.TextInput(
        label="JSON Blueprint",
        style=discord.TextStyle.paragraph,
        placeholder='{"server_name": "...", "roles": [...], "categories": [...]}',
        required=True,
        max_length=4000,
    )

    def __init__(self, guild_id: int) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.submitted_text: Optional[str] = None
        self._event = asyncio.Event()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.submitted_text = self.blueprint_input.value
        # Defer so we can send follow-ups from outside this modal
        await interaction.response.defer(ephemeral=True, thinking=True)
        self._event.set()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(
            f"❌ An error occurred: {error}", ephemeral=True
        )
        self._event.set()

    async def wait_for_submit(self, timeout: float = 300.0) -> bool:
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
            return self.submitted_text is not None
        except asyncio.TimeoutError:
            return False


class BuildConfirmView(discord.ui.View):
    """Approve / Cancel buttons shown after validating the blueprint."""

    def __init__(self, owner_id: int, timeout: float = 120.0) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.value: Optional[bool] = None
        self.response_interaction: Optional[discord.Interaction] = None

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Only the person who ran `/build` can confirm or cancel.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._check_owner(interaction):
            return
        self.value = True
        self.response_interaction = interaction
        await interaction.response.defer(ephemeral=True, thinking=True)
        self._disable_all()
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._check_owner(interaction):
            return
        self.value = False
        self.response_interaction = interaction
        await interaction.response.send_message("❌ Build cancelled.", ephemeral=True)
        self._disable_all()
        self.stop()

    def _disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self) -> None:
        self.value = None
        self._disable_all()


# ================================================
# Copyright (c) 2025 TIS199
# Licensed for Educational and Testing Use Only.
# Redistribution or commercial use is strictly prohibited.
# GitHub: https://github.com/TIS199
# ================================================
