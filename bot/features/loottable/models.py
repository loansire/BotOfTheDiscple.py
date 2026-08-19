# -*- coding: utf-8 -*-
"""Modèles de données Table de butin.

Volontairement proches de `XurItem` (même pipeline de résolution d'item), mais
sans notion de coût : à la place, les caractéristiques d'arme (sous-type,
élément, munitions) conservées sous leur forme NUMÉRIQUE. La traduction en
emoji/libellé est un choix de rendu, pas de donnée : elle vit dans constants.py
et n'est appliquée que côté embeds."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LootItem:
    """Un item d'une table de butin (résolu via DestinyInventoryItemDefinition)."""
    item_hash: int
    name: str
    icon: str | None = None          # displayProperties.icon (chemin relatif)
    watermark: str | None = None     # iconWatermark (chemin relatif), si présent
    is_exotic: bool = False          # rareté exotique (tierType 6)
    craftable: bool = False          # schéma extractible (Souvenance)
    sub_type: int | None = None      # itemSubType (fusil auto, arc…)
    damage_type: int | None = None   # defaultDamageType (arc, solaire…)
    ammo_type: int | None = None     # equippingBlock.ammoType (1/2/3)

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "exotic": self.is_exotic,
            "craftable": self.craftable,
            "sub_type": self.sub_type,
            "damage_type": self.damage_type,
            "ammo_type": self.ammo_type,
        }


@dataclass
class LootActivity:
    """Une activité et sa table de butin (une entrée de loot_tables.json)."""
    key: str                      # identifiant interne (clé JSON)
    label: str                    # nom affiché
    banner: str | None = None     # nom de fichier dans Ressources/ActivityBanner/
    type: str | None = None       # type d'activité normalisé (prestige, destination…)
    items: list[LootItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "banner": self.banner,
            "type": self.type,
            "items": [it.to_dict() for it in self.items],
        }
