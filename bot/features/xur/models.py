# -*- coding: utf-8 -*-
"""Modèles de données Xûr.

Un `XurVendor` correspond à un des 3 marchands (Armes / Ressources / Armures)
et contient la liste des `XurItem` qu'il vend cette semaine. Le champ `extra`
est un point de greffe pour d'éventuelles infos maison (non utilisé pour
l'instant)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class XurPerk:
    """Une perk affichée (colonne 3 ou 4) d'une arme légendaire de Xûr.

    `plug_hash` sert à la fois d'identité et de cible du lien d2glossary.fr.
    `name` est le nom FR (résolu via l'extrait manifest local, item_names_fr.json,
    qui couvre aussi les plugs)."""
    plug_hash: int
    name: str

    def to_dict(self) -> dict:
        return {"plug_hash": self.plug_hash, "name": self.name}


@dataclass
class XurItem:
    """Un item vendu par Xûr (résolu via DestinyInventoryItemDefinition)."""
    item_hash: int
    name: str
    icon: str | None = None            # displayProperties.icon (chemin relatif)
    watermark: str | None = None       # iconWatermark (chemin relatif), si présent
    cost_quantity: int | None = None   # quantité du 1er coût (sales.data[].costs[0].quantity)
    quantity: int = 1                  # nb d'occurrences du même itemHash (cases retenues)
    perks: list[XurPerk] = field(default_factory=list)  # col 3/4 (armes légendaires uniquement)
    craftable: bool = False            # arme légendaire façonnable (schéma extractible / Souvenance)
    # Détail arme / armure (même sémantique que vanguard.FocusItem) ; vide pour
    # catalyseurs, ressources, etc.
    sub_type: int | None = None        # DestinyItemSubType (arme ou pièce d'armure)
    damage_type: int | None = None     # defaultDamageType (armes)
    ammo_type: int | None = None       # equippingBlock.ammoType (armes)
    set_name: str | None = None        # set d'armure
    set_perks: list[tuple[int, str, int]] = field(default_factory=list)  # (nb pièces, bonus, perk hash)

    def to_dict(self) -> dict:
        return {
            "item_hash": self.item_hash,
            "name": self.name,
            "icon": self.icon,
            "watermark": self.watermark,
            "cost_quantity": self.cost_quantity,
            "quantity": self.quantity,
            "perks": [p.to_dict() for p in self.perks],
            "craftable": self.craftable,
            "sub_type": self.sub_type,
            "damage_type": self.damage_type,
            "ammo_type": self.ammo_type,
            "set_name": self.set_name,
            "set_perks": [list(p) for p in self.set_perks],
        }


@dataclass
class XurVendor:
    """Un des 3 vendors de Xûr (catégorie d'affichage)."""
    key: str                # "weapons" / "materials" / "armor"
    label: str              # "Armes" / "Ressources" / "Armures"
    emoji: str
    large_icon: str | None = None   # displayProperties.largeIcon (chemin relatif), image d'en-tête
    items: list[XurItem] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "emoji": self.emoji,
            "large_icon": self.large_icon,
            "items": [it.to_dict() for it in self.items],
            "extra": self.extra,
        }