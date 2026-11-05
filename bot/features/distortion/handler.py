# -*- coding: utf-8 -*-
"""Publication de la Distorsion : message ÉDITÉ EN PLACE chaque heure.

Aucun ping et position conservée dans le salon (pas de repost horaire). La
mécanique (idempotence par hash, rattrapage, réparation) est partagée avec les
Défis ascendants : cf. bot/publishing/edit_in_place.py.

Calcul : presenter.build_post() → base. Publication : lecture de la base."""
from __future__ import annotations

from bot.compute import store
from bot.features.distortion import TOPIC
from bot.features.distortion.presenter import build_post
from bot.features.distortion.state import distortion_state
from bot.publishing.edit_in_place import EditInPlaceTopic

TAG = "Distortion"


async def produce(force: bool = False) -> None:
    """Calcule la distorsion courante et la range en base (nouvelle version
    seulement au changement d'heure)."""
    await store(build_post(), TAG)


publication = EditInPlaceTopic(
    topic=TOPIC,
    tag=TAG,
    state=distortion_state,
    produce=produce,
)
