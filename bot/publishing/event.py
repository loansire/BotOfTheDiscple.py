# -*- coding: utf-8 -*-
"""Publication ÉVÉNEMENTIELLE : un nouveau message par événement (news,
maintenance). Aucun état de message : l'historique reste dans le salon."""
from __future__ import annotations

from typing import Callable

import discord

from bot.core.logger import log
from bot.publishing.primitives import iter_destinations


async def publish_to_subscribers(bot: discord.Client, topic: str, build: Callable):
    """`build()` doit renvoyer (embed, files, view) NEUFS à chaque appel
    (un discord.File est consommé après envoi)."""
    for _, _, dest, info in iter_destinations(bot, topic):
        role_id = info.get("role")
        mention = f"<@&{role_id}>" if role_id else None
        try:
            # build() DANS le try : un échec pour un abonné ne doit pas
            # interrompre la boucle (les autres serveurs seraient privés du
            # message, puis re-servis en double au poll suivant).
            embed, files, view = build()
            if view:
                await dest.send(content=mention, embed=embed, files=files, view=view)
            else:
                await dest.send(content=mention, embed=embed, files=files)
        except Exception as e:
            log.error(f"[Publisher] Envoi échoué dans {dest} ({topic}) : {e}")
