# -*- coding: utf-8 -*-
"""Cog /botconfig : interface admin unifiée d'abonnement aux alertes.

Remplace l'ancienne commande /alerte (cog subscriptions). Toute la
configuration (salons + rôles, par topic) se fait via une vue éphémère
Components V2 avec validation différée.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.discord.configbot_view import ConfigView


class ConfigBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="botconfig",
        description="Configurer les alertes du serveur (salons + rôles).",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def botconfig(self, interaction: discord.Interaction):
        view = ConfigView.start(interaction.user, interaction.guild)
        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigBot(bot))
