# -*- coding: utf-8 -*-
"""Publication de la Distorsion : message ÉDITÉ EN PLACE chaque heure.

Aucun ping et position conservée dans le salon (pas de repost horaire). La
mécanique (idempotence par hash, rattrapage, réparation) est partagée avec les
Défis ascendants : cf. bot/publishing/edit_in_place.py."""
from __future__ import annotations

from bot.features.distortion import TOPIC
from bot.features.distortion.state import distortion_state
from bot.features.distortion.view import build_distortion_view, content_hash
from bot.publishing.edit_in_place import EditInPlaceTopic

publication = EditInPlaceTopic(
    topic=TOPIC,
    tag="Distortion",
    state=distortion_state,
    build=lambda now, _: build_distortion_view(now),
    chash=lambda now, _: content_hash(now),
)
