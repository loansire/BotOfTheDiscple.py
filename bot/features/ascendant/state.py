# -*- coding: utf-8 -*-
"""État persistant des messages Défis ascendants (un message par serveur abonné).

On NE persiste PAS le défi actif (recalculable à tout instant depuis l'ancre).
On persiste seulement, par serveur : l'id du message publié et un `hash`
identifiant la semaine actuellement affichée. Si le hash stocké diffère de la
semaine courante → le message est édité (avance d'un cran). Ce mécanisme assure
aussi le rattrapage automatique après une coupure du bot.

Schéma (Ressources/AlertDatabase/ascendant_state.json) :
    { "<guild_id>": { "message_id": "<id>" | null, "hash": "<str>" | null } }
"""
from functools import cache

from bot.core.config import ALERTS_DIR
from bot.storage.json_store import SingleMessageState

STORE_PATH = ALERTS_DIR / "ascendant_state.json"


@cache
def ascendant_state() -> SingleMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig) : une
    seule copie mémoire écrit ce fichier."""
    return SingleMessageState(STORE_PATH)
