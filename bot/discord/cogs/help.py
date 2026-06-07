# -*- coding: utf-8 -*-
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

# Commandes réservées aux admins (abonnements) → masquées du /help public
HIDDEN_COMMANDS = {"maintenance-alert", "news-alert"}


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Liste des commandes disponibles")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="__Liste des Commandes__",
            colour=0x00F1F5,
            timestamp=datetime.now(),
        )
        embed.set_thumbnail(
            url="https://cdn.icon-icons.com/icons2/272/PNG/512/Settings_30027.png"
        )

        visible = [
            cmd
            for cmd in self.bot.tree.get_commands()
            if cmd.name not in HIDDEN_COMMANDS
        ]
        visible.sort(key=lambda c: c.name)

        embed.description = "".join(
            f"**__/{cmd.name}__**\n> {cmd.description}\n\n" for cmd in visible
        )
        embed.set_footer(text=f"{len(visible)} commande(s) disponible(s)")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))