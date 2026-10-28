# -*- coding: utf-8 -*-
"""Cog des rotations FIXES (Distorsion horaire, Défi ascendant hebdo).

Rotations déterministes, sans dépendance au reset Bungie : un poll/min détecte
le changement de période via le `content_hash` et ré-édite les salons périmés
(aucun ping). Couvre aussi le rattrapage au démarrage (période changée pendant
une coupure) et la réparation des messages supprimés à la main.

Chaque publication est isolée : l'échec de l'une n'empêche pas l'autre."""
from discord.ext import commands, tasks

from bot.core.logger import log
from bot.features.ascendant.handler import publication as ascendant
from bot.features.distortion.handler import publication as distortion

PUBLICATIONS = (distortion, ascendant)


class Rotations(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    @tasks.loop(minutes=1)
    async def poll(self):
        for publication in PUBLICATIONS:
            try:
                await publication.publish(self.bot)
            except Exception as e:
                log.error(f"[{publication.tag}] poll échoué : {e}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Rotations(bot))
