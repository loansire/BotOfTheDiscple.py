# -*- coding: utf-8 -*-
"""État des messages persistants Eververse.

Un seul rôle de message : les messages de sections, stockés à plat par guild.
JETABLES : supprimés puis republiés à chaque changement de contenu (repost →
notification + ping rôle). Persisté en base (bot/storage/messages.py), topic
`eververse`.

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique source
de vérité (PipelineState).

Le `hash` (calculé par le handler : id de reset + itemHash) évite de reposter un
contenu inchangé. Le refresh manuel passe par `invalidate()` ; le retrait d'un
salon via /botconfig passe par `purge()`."""
from functools import cache

from bot.storage.messages import MultiMessageState


@cache
def eververse_state() -> MultiMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig)."""
    return MultiMessageState("eververse")
