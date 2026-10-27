# -*- coding: utf-8 -*-
"""Enregistrement des vues PERSISTANTES (boutons qui survivent au redémarrage).

Aucune commande : l'extension appelle `bot.add_view()` une fois au chargement,
pour que les boutons des messages déjà publiés restent cliquables après un
redémarrage du bot. Ajouter ici toute future vue persistante.
"""
from discord.ext import commands

from bot.core.logger import log
from bot.features.weekly.rotation_buttons import RotationPersistentView


async def setup(bot: commands.Bot):
    bot.add_view(RotationPersistentView())
    log.info("[Vues] Vue persistante enregistrée (weekly:rota:raid|dungeon).")
