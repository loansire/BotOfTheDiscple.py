# -*- coding: utf-8 -*-
"""Modèles de données Xûr.

Un `XurVendor` correspond à un des 3 marchands (Armes / Ressources / Armures)
et contient la liste des `XurItem` qu'il vend cette semaine. Le champ `extra`
est un point de greffe pour d'éventuelles infos maison (non utilisé pour
l'instant)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class XurItem:
    """Un item vendu par Xûr (résolu via DestinyInventoryItemDefinition)."""
    item_hash: int
    name: str
    icon: str | None = None            # displayProperties.icon (chemin relatif)
    watermark: str | None = None       # iconWatermark (chemin relatif), si présent
    cost_quantity: int | None = None   # quantité du 1er coût (sales.data[].costs[0].quantity)

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "cost_quantity": self.cost_quantity,
        }


@dataclass
class XurVendor:
    """Un des 3 vendors de Xûr (catégorie d'affichage)."""
    key: str                # "weapons" / "materials" / "armor"
    label: str              # "Armes" / "Ressources" / "Armures"
    emoji: str
    items: list[XurItem] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "emoji": self.emoji,
            "items": [it.to_dict() for it in self.items],
            "extra": self.extra,
        }