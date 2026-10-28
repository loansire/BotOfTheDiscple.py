# -*- coding: utf-8 -*-
"""État des messages persistants Eververse.

Un seul rôle de message : les 3 messages de sections (principales / autres /
Argentum), stockés à plat par guild. JETABLES : supprimés puis republiés à
chaque changement de contenu (repost → notification + ping rôle).

{
  "guilds": {
    "<guild_id>": {
      "message_ids": ["...", "...", "..."],
      "hash": "..."
    }
  }
}

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique source
de vérité (PipelineState). Une éventuelle clé `last_reset` héritée est purgée au
chargement.

Le `hash` (calculé par le handler : id de reset + itemHash) évite de reposter un
contenu inchangé. Le refresh manuel passe par `invalidate()` ; le retrait d'un
salon via /botconfig passe par `purge()`."""
from functools import cache

from bot.core.config import ALERTS_DIR
from bot.storage.json_store import MultiMessageState

STATE_PATH = ALERTS_DIR / "eververse_messages.json"


@cache
def eververse_state() -> MultiMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig) : une
    seule copie mémoire écrit ce fichier."""
    return MultiMessageState(STATE_PATH)
