# -*- coding: utf-8 -*-
"""Tri des activités du Portail (logique pure, sans I/O réseau).

Une activité est retenue si l'API la marque en focus (`isFocusedActivity`) ou
si elle a des challenges actifs (activités « défi », ex. Berceau du mal), ET si
elle appartient à une catégorie publiée d'après l'extrait Portail du manifest
(cf. ManifestStore.portal).

Défis : les challenges sont lus sur le profil du personnage de référence et
disparaissent une fois le défi accompli, alors que le défi (et son arme) tourne
à la SEMAINE. `remembered` ({activity_hash: arme défi}) permet de réafficher un
défi vu plus tôt dans la semaine (mémorisé par le handler)."""
from __future__ import annotations

from .constants import CATEGORIES, OPS_BONUS_REWARD
from .models import PortalActivity, PortalCategory

_PLACEHOLDER = "placeholder"

# Suffixes de variante qui ne sont PAS des difficultés (mode de lancement).
_NOT_DIFFICULTY = {"Matchmaking", "Personnalisation", "Privé"}


def base_name(name: str) -> str:
    """'Champ de bataille : Conduit: Matchmaking' → 'Champ de bataille : Conduit'.

    Découpe sur le DERNIER ': ' (le nom de base peut lui-même contenir ' : ').
    Les espaces insécables du manifest FR sont normalisés."""
    name = name.replace("\xa0", " ")
    return name.rsplit(": ", 1)[0].strip() if ": " in name else name.strip()


def variant_label(name: str) -> str | None:
    """'Partie rapide : Maîtrise' → 'Maîtrise' ; None si pas de suffixe."""
    name = name.replace(" ", " ")
    return name.rsplit(": ", 1)[1].strip() if ": " in name else None


def focus_item_hash(raw: dict) -> int | None:
    """Item focus d'une activité : 1re récompense CONDITIONNELLE autre que le
    bonus commun des Opérations."""
    for reward in raw.get("visibleRewards", []):
        for item in reward.get("rewardItems", []):
            qty = item.get("itemQuantity", {})
            ih = qty.get("itemHash")
            if qty.get("hasConditionalVisibility") and ih and ih != OPS_BONUS_REWARD:
                return ih
    return None


def _real_pgcr(adef: dict) -> str | None:
    pgcr = adef.get("pgcrImage") or ""
    return pgcr if pgcr and _PLACEHOLDER not in pgcr else None


def pgcr_for(adef: dict, defs: dict) -> str | None:
    """Bandeau de l'activité. Certaines activités du Portail n'ont qu'un
    placeholder : repli sur le 1er élément de leur playlist, puis sur une autre
    définition portant le même nom de base (ex. la carte de l'Épreuve)."""
    pgcr = _real_pgcr(adef)
    if pgcr:
        return pgcr
    for item in adef.get("playlistItems", []):
        pgcr = _real_pgcr(defs.get(str(item.get("activityHash")), {}))
        if pgcr:
            return pgcr
    name = base_name(adef.get("displayProperties", {}).get("name", ""))
    for other in defs.values():
        # Nom complet OU nom de base : une définition sans suffixe de variante
        # (« Surcharge : La Côte enchevêtrée ») serait sinon tronquée.
        other_name = other.get("displayProperties", {}).get("name", "")
        if name in (other_name.replace("\xa0", " ").strip(), base_name(other_name)):
            pgcr = _real_pgcr(other)
            if pgcr:
                return pgcr
    return None


def collect_portal(
    activities: list[dict],
    manifest,
    portal: dict,
    remembered: dict[int, int] | None = None,
) -> list[PortalCategory]:
    """Regroupe les activités focus/défi par catégorie du Portail.

    Ordre des catégories = CATEGORIES ; dans une catégorie, alerte grand maître
    puis alerte Escouade, puis ordre de l'API. Une catégorie sans activité est conservée (vide)."""
    remembered = dict(remembered or {})
    by_root = {
        int(root): set(hashes)
        for root, hashes in (portal.get("categories") or {}).items()
    }
    alerts = set(portal.get("alerts") or [])
    grandmaster = set(portal.get("grandmaster") or [])
    defs = manifest.definitions("DestinyActivityDefinition")

    categories = [PortalCategory(key, label, icon) for key, _, label, icon in CATEGORIES]
    groups: list[dict[str, PortalActivity]] = [{} for _ in CATEGORIES]

    # Défis mémorisés absents du profil (déjà accomplis) : réinjectés tels quels.
    seen = {raw.get("activityHash") for raw in activities}
    extra = [{"activityHash": ah, "challenges": [None]} for ah in remembered if ah not in seen]

    for raw in [*activities, *extra]:
        ah = raw.get("activityHash")
        challenges = len(raw.get("challenges", []))
        is_challenge = challenges > 0 or ah in remembered
        if not raw.get("isFocusedActivity") and not is_challenge:
            continue
        idx = next(
            (i for i, (_, root, _, _) in enumerate(CATEGORIES) if ah in by_root.get(root, ())),
            None,
        )
        if idx is None:
            continue

        adef = defs.get(str(ah), {})
        full_name = adef.get("displayProperties", {}).get("name", "")
        name = base_name(full_name)
        if not name:
            continue

        act = groups[idx].get(name)
        if act is None:
            act = PortalActivity(base_name=name, pgcr_image=pgcr_for(adef, defs))
            groups[idx][name] = act
        act.activity_hashes.append(ah)
        act.focus_hash = act.focus_hash or focus_item_hash(raw) or remembered.get(ah)
        act.is_focused = act.is_focused or bool(raw.get("isFocusedActivity"))
        act.is_grandmaster = act.is_grandmaster or ah in grandmaster
        act.is_alert = (act.is_alert or ah in alerts) and not act.is_grandmaster
        label = variant_label(full_name)
        if label and label not in _NOT_DIFFICULTY and label not in act.difficulties:
            act.difficulties.append(label)
        act.is_challenge = act.is_challenge or is_challenge

    for cat, group in zip(categories, groups):
        cat.activities = sorted(
            group.values(), key=lambda a: (not a.is_grandmaster, not a.is_alert)
        )
    return categories


def challenges_of(categories: list[PortalCategory]) -> dict[int, int]:
    """{activity_hash: arme défi} des activités défi (sans focus) à mémoriser
    pour la semaine."""
    return {
        ah: act.focus_hash
        for cat in categories
        for act in cat.activities
        if act.is_challenge and not act.is_focused and act.focus_hash
        for ah in act.activity_hashes
    }
