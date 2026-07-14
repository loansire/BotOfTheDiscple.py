# -*- coding: utf-8 -*-
"""Modèles de données Eververse.

Une `EververseSection` = un des 3 messages d'affichage (principales / autres /
Argentum). Elle contient ses `EververseItem` dans l'ordre voulu. `currency`
détermine si le coût est affiché (dust) ou masqué (silver)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EververseItem:
    """Un item en vente (résolu via DestinyInventoryItemDefinition)."""
    item_hash: int
    name: str
    icon: str | None = None            # displayProperties.icon (chemin relatif)
    watermark: str | None = None       # iconWatermark (chemin relatif), si présent
    cost_quantity: int | None = None   # quantité du 1er coût (costs[0].quantity)
    currency: str = "dust"             # "dust" | "silver" (hérité de la section)

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "cost_quantity": self.cost_quantity,
            "currency": self.currency,
        }


@dataclass
class EververseSection:
    """Une des 3 sections d'affichage (1 message chacune)."""
    id: str                 # "main" | "other" | "silver"
    title: str
    currency: str           # "dust" | "silver"
    items: list[EververseItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "currency": self.currency,
            "items": [it.to_dict() for it in self.items],
        }