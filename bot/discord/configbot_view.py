# -*- coding: utf-8 -*-
"""Vue principale de /botconfig (Components V2, éphémère, stateful).

Navigation : `current_topic` détermine la page affichée
(None = accueil, sinon page détail d'un topic). Chaque interaction
reconstruit une ConfigView neuve en transportant `persisted`, `pending`
et `current_topic`.
"""
import copy

import discord
from discord import ui

from bot.discord.configbot_builder import build_config_components
from bot.utils.subscriptions import load_config_state


class ConfigView(ui.LayoutView):
    def __init__(
        self,
        user: discord.Member,
        guild: discord.Guild,
        persisted: dict,
        pending: dict,
        current_topic: str | None = None,
    ):
        super().__init__(timeout=180)
        self.user = user
        self.guild = guild
        self.persisted = persisted
        self.pending = pending
        self.current_topic = current_topic

        for comp in build_config_components(guild, persisted, pending, current_topic):
            self.add_item(comp)

    @classmethod
    def start(cls, user: discord.Member, guild: discord.Guild) -> "ConfigView":
        """Charge l'état persistant et ouvre la page principale (pending == persisted)."""
        persisted = load_config_state(guild.id)
        pending = copy.deepcopy(persisted)
        return cls(user, guild, persisted, pending, current_topic=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "🚫 Cette configuration ne t'appartient pas.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        self.stop()