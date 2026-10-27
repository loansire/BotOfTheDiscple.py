# -*- coding: utf-8 -*-
"""Publication des Défis ascendants : message ÉDITÉ EN PLACE à chaque reset hebdo.

Comme la Distorsion (cf. bot/publishing/edit_in_place.py) : aucun ping,
position conservée, rattrapage et réparation automatiques.

Source de vérité : la formule déterministe. Le contrat live de Petra
(composant 402, mémoïsé par semaine) est passé en override de validation à la
vue et au hash : resolve() gère l'override et loggue toute divergence."""
from __future__ import annotations

from bot.features.ascendant import TOPIC
from bot.features.ascendant.service import fetch_contrat_hash, reset_cache
from bot.features.ascendant.state import ascendant_state
from bot.features.ascendant.view import build_ascendant_view, content_hash
from bot.publishing.edit_in_place import EditInPlaceTopic

publication = EditInPlaceTopic(
    topic=TOPIC,
    tag="Ascendant",
    state=ascendant_state,
    build=build_ascendant_view,
    chash=content_hash,
    context=fetch_contrat_hash,  # None → repli formule
    reset_context=reset_cache,
)
