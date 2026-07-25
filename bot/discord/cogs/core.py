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
        # Chaque sync est ISOLÉE dans son propre try/except. Sans ça, une
        # commande mal formée (ex. description vide → HTTP 400 côté Discord)
        # faisait lever `sync()` en tête de on_ready, et TOUT ce qui suit — dont
        # le log « Bot prêt » — était silencieusement zappé : le bot paraissait
        # ne jamais démarrer. Désormais l'échec devient un log.error explicite
        # (nommant la sync fautive) et le message de démarrage passe TOUJOURS.

        # Commandes globales (visibles sur tous les serveurs).
        try:
            await self.bot.tree.sync()
        except Exception as e:
            log.error(f"Échec de la sync GLOBALE des commandes : {e}")

        # Commandes DE GUILDE du serveur de contrôle (ex. /refresh, /wish-wall) :
        # sans ce sync ciblé, une commande scopée à une guilde n'apparaîtrait
        # jamais.
        if CONTROL_GUILD_ID:
            guild = discord.Object(id=CONTROL_GUILD_ID)
            try:
                await self.bot.tree.sync(guild=guild)
                log.info(
                    f"Commandes du serveur de contrôle synchronisées ({CONTROL_GUILD_ID})."
                )
            except Exception as e:
                log.error(
                    f"Échec de la sync du SERVEUR DE CONTRÔLE "
                    f"({CONTROL_GUILD_ID}) : {e}"
                )

        log.info(f"Bot prêt — connecté en tant que {self.bot.user}")
        for cmd in self.bot.tree.get_commands():
            log.info(f"Commande disponible : /{cmd.name}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Core(bot))