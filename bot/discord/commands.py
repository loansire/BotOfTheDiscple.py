# -*- coding: utf-8 -*-
from discord.ext import commands

from bot.utils.logger import log

# Liste centrale des cogs à charger
COGS = (
    "bot.discord.cogs.core",
    "bot.discord.cogs.help",
    "bot.discord.cogs.news",
    "bot.discord.cogs.maintenance",
    "bot.discord.cogs.randomizer",
    "bot.discord.cogs.wishwall",
    "bot.discord.cogs.alerts",
    "bot.discord.cogs.configbot",
)


async def setup(bot: commands.Bot):
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            log.info(f"Cog chargé : {cog}")
        except Exception as e:
            log.error(f"Échec du chargement de {cog} : {e}")
