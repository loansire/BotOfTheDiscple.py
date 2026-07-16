# -*- coding: utf-8 -*-
"""Modèles de données Eververse.

Une `EververseSection` = un des messages d'affichage (principales / autres).
Elle contient ses `EververseItem` dans l'ordre voulu. `currency` détermine si
le coût est affiché (dust)."""
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
    currency: str = "dust"             # "dust" (hérité de la section)
    # Libellé de classe, affiché AU-DESSUS du coût (vendor d'ornements d'armure
    # multi-classe : "Ornement Titan" / "Ornement Arcaniste" / "Ornement
    # Chasseur"). None pour les items normaux.
    class_label: str | None = None

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "cost_quantity": self.cost_quantity,
            "currency": self.currency,
            "class_label": self.class_label,
        }


@dataclass
class EververseSection:
    """Une des sections d'affichage (1 message chacune)."""
    id: str                 # "main" | "other"
    title: str
    currency: str           # "dust"
    items: list[EververseItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "currency": self.currency,
            "items": [it.to_dict() for it in self.items],
        }