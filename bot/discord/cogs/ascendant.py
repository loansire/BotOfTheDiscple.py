# -*- coding: utf-8 -*-
"""Cog Défis ascendants : édite chaque semaine le message persistant de rotation.

Rotation FIXE déterministe (aucun appel Bungie). Un poll/min détecte le
changement de semaine via le `content_hash` : les salons dont la semaine
affichée est périmée sont ré-édités (aucun ping). Couvre aussi :
- le rattrapage au démarrage (semaine changée pendant une coupure) ;
- la réparation des messages supprimés à la main (renvoi si le message a disparu).

L'état des messages (`self.state`) est exposé pour le routeur /botconfig
(bot.discord.handlers.topics.apply_config_change)."""
from discord.ext import commands, tasks

from bot.discord.handlers import ascendant as handler
from bot.features.ascendant.state import AscendantMessageState
from bot.utils.logger import log


class Ascendant(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = AscendantMessageState()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    @tasks.loop(minutes=1)
    async def poll(self):
        try:
            await handler.publish(self.bot, self.state)
        except Exception as e:
            log.error(f"[Ascendant] poll échoué : {e}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Ascendant(bot))
