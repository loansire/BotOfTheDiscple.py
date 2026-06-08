# -*- coding: utf-8 -*-
"""Vue principale de /botconfig (Components V2, éphémère, stateful).

Stratégie de re-render : chaque interaction reconstruit une ConfigView neuve
en transportant `persisted` (état en base) et `pending` (état en cours).
"""
import copy

import discord
from discord import ui

from bot.discord.configbot_builder import build_config_components, is_dirty
from bot.discord.configbot_components import ResetButton, ValidateButton
from bot.utils.subscriptions import load_config_state


class ConfigView(ui.LayoutView):
    def __init__(self, user: discord.Member, guild: discord.Guild, persisted: dict, pending: dict):
        super().__init__(timeout=180)
        self.user = user
        self.guild = guild
        self.persisted = persisted
        self.pending = pending

        for comp in build_config_components(guild, persisted, pending):
            self.add_item(comp)

        if is_dirty(persisted, pending):
            self.add_item(ui.ActionRow(ValidateButton(), ResetButton()))

    @classmethod
    def start(cls, user: discord.Member, guild: discord.Guild) -> "ConfigView":
        """Charge l'état persistant et ouvre une vue 'propre' (pending == persisted)."""
        persisted = load_config_state(guild.id)
        pending = copy.deepcopy(persisted)
        return cls(user, guild, persisted, pending)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "🚫 Cette configuration ne t'appartient pas.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        self.stop()
