# -*- coding: utf-8 -*-
"""Cog d'enregistrement de la vue persistante « Rotation prédictive ».

Aucune commande : ce cog existe uniquement pour appeler `bot.add_view()` une
fois au chargement, afin que les boutons des messages raids/donjons déjà
publiés restent cliquables après un redémarrage du bot.
"""
from discord.ext import commands

from bot.discord.rotation_components import RotationPersistentView
from bot.utils.logger import log


class Rotation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    bot.add_view(RotationPersistentView())
    log.info("[Rotation] Vue persistante enregistrée (weekly:rota:raid|dungeon).")
    await bot.add_cog(Rotation(bot))