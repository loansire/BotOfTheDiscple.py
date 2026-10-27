# -*- coding: utf-8 -*-
"""Modèles de la feature Avant-garde."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FocusItem:
    """Récompense focus d'une activité (arme ou armure)."""
    item_hash: int
    name: str
    sub_type: int | None = None      # DestinyItemSubType (arme ou pièce d'armure)
    damage_type: int | None = None   # defaultDamageType (armes)
    ammo_type: int | None = None     # equippingBlock.ammoType (armes)
    icon: str | None = None
    watermark: str | None = None
    # Armures : set d'équipement et ses bonus [(nb de pièces, nom, sandboxPerkHash)].
    set_name: str | None = None
    set_perks: list[tuple[int, str, int]] = field(default_factory=list)


@dataclass
class PortalActivity:
    """Une activité du Portail (variantes Normal/Maîtrise, Matchmaking/
    Personnalisation regroupées sous le même nom de base)."""
    base_name: str
    activity_hashes: list[int] = field(default_factory=list)
    pgcr_image: str | None = None
    focus_hash: int | None = None       # résolu ensuite en `focus`
    focus: FocusItem | None = None
    is_focused: bool = False            # isFocusedActivity (sinon : défi seul)
    is_alert: bool = False              # alerte de l'Avant-garde
    is_challenge: bool = False          # défi de la semaine (engramme + arme défi)


@dataclass
class PortalCategory:
    """Une catégorie du Portail (Escouade, Prestige, Arène, Solo)."""
    key: str
    label: str
    icon_file: str
    activities: list[PortalActivity] = field(default_factory=list)
