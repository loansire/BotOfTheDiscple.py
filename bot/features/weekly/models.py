# -*- coding: utf-8 -*-
"""Modèles de données pour les activités weekly/daily.

Chaque activité (raid, donjon, secteur perdu) est regroupée par nom de base,
ses différentes difficultés étant conservées comme variantes distinctes.
Le champ `extra` (présent à chaque niveau) est un point de greffe pour des
infos maintenues à la main, que l'API ne fournit pas (boucliers, champions,
notes…). Il est vide tant qu'aucune donnée n'est greffée.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActivityVariant:
    """Une difficulté précise d'une activité (Standard, Maîtrise, Expert…)."""
    activity_hash: int
    label: str
    recommended_light: int | None = None
    difficulty_tier: int | None = None
    modifier_hashes: list[int] = field(default_factory=list)
    active_challenges: int = 0  # nb de challenges actifs (signal "featured")
    featured_reward: bool = False  # récompense conditionnelle palier 5 (signal "featured")
    extra: dict = field(default_factory=dict)  # greffe maison par activity_hash

    def to_dict(self) -> dict:
        d = {
            "activity_hash": self.activity_hash,
            "label": self.label,
            "modifier_hashes": self.modifier_hashes,
        }
        if self.recommended_light is not None:
            d["recommended_light"] = self.recommended_light
        if self.difficulty_tier is not None:
            d["difficulty_tier"] = self.difficulty_tier
        if self.active_challenges:
            d["active_challenges"] = self.active_challenges
        if self.featured_reward:
            d["featured_reward"] = True
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class WeeklyActivity:
    """Un raid ou un donjon (toutes difficultés regroupées)."""
    base_name: str
    activity_type: str          # "Raid" / "Donjon"
    type_hash: int
    pgcr_image: str | None = None
    permanent: bool = False     # contenu permanent (le plus récent), défini via JSON
    variants: list[ActivityVariant] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    @property
    def featured(self) -> bool:
        """Featured cette semaine si au moins une variante a un challenge actif
        OU une récompense conditionnelle de palier 5.

        Heuristique : l'API n'expose pas de drapeau "featured" sur le contenu
        Director. Deux signaux, l'un ou l'autre suffit :
        - challenges actifs (`challenges` non vide dans le composant 204) ;
        - récompense featured (cf. filters.FEATURED_REWARD_HASHES) : certaines
          activités en rotation n'ont AUCUN challenge (ex. Étreinte de
          l'Avarice, semaine du 20/10/2026) mais affichent l'engramme palier 5
          au lieu du palier 3.
        Seul point à toucher si Bungie change la mécanique."""
        return any(v.active_challenges > 0 or v.featured_reward for v in self.variants)

    def to_dict(self) -> dict:
        return {
            "base_name": self.base_name,
            "activity_type": self.activity_type,
            "type_hash": self.type_hash,
            "pgcr_image": self.pgcr_image,
            "permanent": self.permanent,
            "featured": self.featured,
            "variants": [v.to_dict() for v in self.variants],
            "extra": self.extra,
        }


@dataclass
class LostSector:
    """Un secteur perdu (1 par planète, difficultés Expert/Maîtrise)."""
    base_name: str
    destination: str | None = None   # planète, via destinationHash
    pgcr_image: str | None = None
    variants: list[ActivityVariant] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "base_name": self.base_name,
            "destination": self.destination,
            "pgcr_image": self.pgcr_image,
            "variants": [v.to_dict() for v in self.variants],
            "extra": self.extra,
        }