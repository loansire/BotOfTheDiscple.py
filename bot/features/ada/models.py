# -*- coding: utf-8 -*-
"""Modèles de données Ada-1.

Un `AdaItem` = un item vendu par Ada-1 cette semaine (résolu via
DestinyInventoryItemDefinition). Le champ `extra` est un point de greffe pour
d'éventuelles infos maison (non utilisé pour l'instant)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AdaItem:
    """Un item vendu par Ada-1 (résolu via DestinyInventoryItemDefinition).

    `cost_quantity` = quantité du 1er coût (Glimmer). Le nom est résolu en EN
    via l'API live puis surchargé en FR si une traduction existe dans l'extrait
    manifest local (item_names_fr.json)."""
    item_hash: int
    name: str
    icon: str | None = None            # displayProperties.icon (chemin relatif)
    watermark: str | None = None       # iconWatermark (chemin relatif), si présent
    cost_quantity: int | None = None   # quantité du 1er coût (Glimmer)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "cost_quantity": self.cost_quantity,
            "extra": self.extra,
        }