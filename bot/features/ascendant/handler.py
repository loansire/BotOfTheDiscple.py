# -*- coding: utf-8 -*-
"""Publication des Défis ascendants : message ÉDITÉ EN PLACE à chaque reset hebdo.

Comme la Distorsion (cf. bot/publishing/edit_in_place.py) : aucun ping,
position conservée, rattrapage et réparation automatiques.

Source de vérité : la formule déterministe. Le contrat live de Petra
(composant 402, mémoïsé par semaine) est passé en override de validation au
calcul : resolve() gère l'override et loggue toute divergence."""
from __future__ import annotations

from bot.compute import store
from bot.features.ascendant import TOPIC
from bot.features.ascendant.presenter import build_post
from bot.features.ascendant.service import fetch_contrat_hash, reset_cache
from bot.features.ascendant.state import ascendant_state
from bot.publishing.edit_in_place import EditInPlaceTopic

TAG = "Ascendant"


async def produce(force: bool = False) -> None:
    """Calcule le défi de la semaine et le range en base. `force` (/refresh)
    re-tire le contrat de Petra."""
    if force:
        reset_cache()
    contrat = await fetch_contrat_hash()  # None → repli formule
    await store(build_post(hash_contrat=contrat), TAG)


publication = EditInPlaceTopic(
    topic=TOPIC,
    tag=TAG,
    state=ascendant_state,
    produce=produce,
)
