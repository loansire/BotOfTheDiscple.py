# -*- coding: utf-8 -*-
from discord.ext import commands

from bot.utils.logger import log


class Core(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.tree.sync()
        log.info(f"Bot prêt — connecté en tant que {self.bot.user}")
        for cmd in self.bot.tree.get_commands():
            log.info(f"Commande disponible : /{cmd.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))