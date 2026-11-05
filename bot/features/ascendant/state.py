# -*- coding: utf-8 -*-
"""État persistant des messages Défis ascendants (un message par serveur abonné).

On NE persiste PAS le défi actif (recalculable à tout instant depuis l'ancre).
On persiste seulement, par serveur : l'id du message publié et un `hash`
identifiant la semaine actuellement affichée. Si le hash stocké diffère de la
semaine courante → le message est édité (avance d'un cran). Ce mécanisme assure
aussi le rattrapage automatique après une coupure du bot.

Persisté en base (bot/storage/messages.py), topic `ascendant`.
"""
from functools import cache

from bot.storage.messages import SingleMessageState


@cache
def ascendant_state() -> SingleMessageState:
    """Instance UNIQUE partagée (pipeline, cogs, routeur /botconfig)."""
    return SingleMessageState("ascendant")
