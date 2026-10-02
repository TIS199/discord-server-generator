"""
views.py
--------
Discord UI components: modal for pasting JSON blueprint and
confirmation buttons for approving or cancelling a build.
"""

import asyncio
import discord
from typing import Optional


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
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._check_owner(interaction):
            return
        self.value = False
        self.response_interaction = interaction
        self._disable_all()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Build cancelled.", ephemeral=True)
        self.stop()

    def _disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self) -> None:
        self.value = None
        self._disable_all()


class NukeConfirmView(discord.ui.View):
    """Second, explicit confirmation for the destructive /nuke operation."""

    def __init__(self, owner_id: int, timeout: float = 60.0) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.value: Optional[bool] = None
        self.response_interaction: Optional[discord.Interaction] = None

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the administrator who started `/nuke` can confirm it.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Delete server structure", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._check_owner(interaction):
            return
        self.value = True
        self.response_interaction = interaction
        self._disable_all()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await self._check_owner(interaction):
            return
        self.value = False
        self.response_interaction = interaction
        self._disable_all()
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Nuke cancelled; no server data was deleted.", ephemeral=True)
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
