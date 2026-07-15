# -*- coding: utf-8 -*-
"""Vue principale de /botconfig (Components V2, éphémère, stateful).

Navigation multi-pages : `node_id` détermine la page affichée — un nœud de
l'arbre NAV_TREE (racine / jeu / catégorie / feuille) ou "topic:<topic>" pour la
page détail d'un topic. `page` gère la pagination d'une feuille qui dépasse le
plafond de composants. Chaque interaction reconstruit une ConfigView neuve en
transportant `persisted`, `pending`, `node_id` et `page`.
"""
import copy

import discord
from discord import ui

from bot.discord.configbot_builder import ROOT, build_config_components
from bot.utils.subscriptions import load_config_state


class ConfigView(ui.LayoutView):
    def __init__(
        self,
        user: discord.Member,
        guild: discord.Guild,
        persisted: dict,
        pending: dict,
        node_id: str = ROOT,
        page: int = 0,
    ):
        super().__init__(timeout=180)
        self.user = user
        self.guild = guild
        self.persisted = persisted
        self.pending = pending
        self.node_id = node_id
        self.page = page

        for comp in build_config_components(guild, persisted, pending, node_id, page):
            self.add_item(comp)

    @classmethod
    def start(cls, user: discord.Member, guild: discord.Guild) -> "ConfigView":
        """Charge l'état persistant et ouvre la page racine (pending == persisted)."""
        persisted = load_config_state(guild.id)
        pending = copy.deepcopy(persisted)
        return cls(user, guild, persisted, pending, node_id=ROOT, page=0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "🚫 Cette configuration ne t'appartient pas.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self):
        self.stop()