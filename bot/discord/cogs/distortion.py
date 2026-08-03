# -*- coding: utf-8 -*-
"""Cog Distorsion : édite chaque heure le message persistant de rotation.

Rotation FIXE (aucun appel Bungie). Un poll/min détecte le changement d'heure
via le `content_hash` : les salons dont l'heure affichée est périmée sont
ré-édités (aucun ping). Couvre aussi :
- le rattrapage au démarrage (heure changée pendant une coupure) ;
- la réparation des messages supprimés à la main (renvoi si le message a
  disparu).

L'état des messages (`self.state`) est exposé pour le routeur /botconfig
(bot.discord.handlers.topics.apply_config_change)."""
from discord.ext import commands, tasks

from bot.discord.handlers import distortion as handler
from bot.features.distortion.state import DistortionMessageState
from bot.utils.logger import log


class Distortion(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = DistortionMessageState()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    @tasks.loop(minutes=1)
    async def poll(self):
        try:
            await handler.publish(self.bot, self.state)
        except Exception as e:
            log.error(f"[Distortion] poll échoué : {e}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Distortion(bot))
