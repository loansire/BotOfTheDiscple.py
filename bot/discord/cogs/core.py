# -*- coding: utf-8 -*-
import discord
from discord.ext import commands

from bot.config import CONTROL_GUILD_ID
from bot.utils.logger import log


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Commandes globales (visibles sur tous les serveurs).
        await self.bot.tree.sync()

        # Commandes DE GUILDE du serveur de contrôle (ex. /refresh) : sans ce
        # sync ciblé, une commande scopée à une guilde n'apparaîtrait jamais.
        if CONTROL_GUILD_ID:
            guild = discord.Object(id=CONTROL_GUILD_ID)
            await self.bot.tree.sync(guild=guild)
            log.info(
                f"Commandes du serveur de contrôle synchronisées ({CONTROL_GUILD_ID})."
            )

        log.info(f"Bot prêt — connecté en tant que {self.bot.user}")
        for cmd in self.bot.tree.get_commands():
            log.info(f"Commande disponible : /{cmd.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))