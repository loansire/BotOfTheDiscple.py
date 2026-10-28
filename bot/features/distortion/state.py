# -*- coding: utf-8 -*-
"""État persistant des messages Distorsion (un message par serveur abonné).

On NE persiste PAS la distorsion active (recalculable à tout instant depuis
l'ancre). On persiste seulement, par serveur : l'id du message publié et un
`hash` identifiant l'heure actuellement affichée. Si le hash stocké diffère de
l'heure courante → le message est édité (avance d'un cran). Ce mécanisme assure
aussi le rattrapage automatique après une coupure du bot.

Schéma (Ressources/AlertDatabase/distortion_state.json) :
    { "<guild_id>": { "message_id": "<id>" | null, "hash": "<str>" | null } }
"""
from functools import cache

from bot.core.config import ALERTS_DIR
from bot.storage.json_store import SingleMessageState

STORE_PATH = ALERTS_DIR / "distortion_state.json"


@cache
def distortion_state() -> SingleMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig) : une
    seule copie mémoire écrit ce fichier."""
    return SingleMessageState(STORE_PATH)
