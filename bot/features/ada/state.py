# -*- coding: utf-8 -*-
"""État des messages persistants Ada-1.

Un seul rôle de message : le(s) message(s) de contenu (normalement 1, re-découpé
seulement si le plafond CV2 est dépassé), stockés à plat par guild. JETABLES :
supprimés puis republiés à chaque changement de contenu (repost → notification +
ping rôle). Persisté en base (bot/storage/messages.py), topic `ada`.

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique source
de vérité (PipelineState).

Le `hash` (calculé par le handler : id de reset + itemHash) évite de reposter un
contenu inchangé. Le refresh manuel passe par `invalidate()` ; le retrait d'un
salon via /botconfig passe par `purge()`."""
from functools import cache

from bot.storage.messages import MultiMessageState


@cache
def ada_state() -> MultiMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig)."""
    return MultiMessageState("ada")
