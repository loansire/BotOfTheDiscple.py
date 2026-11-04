# -*- coding: utf-8 -*-
"""État persistant des messages Distorsion (un message par serveur abonné).

On NE persiste PAS la distorsion active (recalculable à tout instant depuis
l'ancre). On persiste seulement, par serveur : l'id du message publié et un
`hash` identifiant l'heure actuellement affichée. Si le hash stocké diffère de
l'heure courante → le message est édité (avance d'un cran). Ce mécanisme assure
aussi le rattrapage automatique après une coupure du bot.

Persisté en base (bot/storage/messages.py), topic `distortion`.
"""
from functools import cache

from bot.storage.messages import SingleMessageState


@cache
def distortion_state() -> SingleMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig)."""
    return SingleMessageState("distortion")
