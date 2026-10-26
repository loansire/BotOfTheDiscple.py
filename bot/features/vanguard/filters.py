# -*- coding: utf-8 -*-
"""Tri des activités du Portail (logique pure, sans I/O réseau).

Une activité est retenue si l'API la marque en focus (`isFocusedActivity`) ou
si elle a des challenges actifs (activités « défi », ex. Berceau du mal), ET si
elle appartient à une catégorie publiée d'après l'extrait Portail du manifest
(cf. ManifestStore.portal)."""
from __future__ import annotations

from .constants import CATEGORIES, OPS_BONUS_REWARD
from .models import PortalActivity, PortalCategory


def base_name(name: str) -> str:
    """'Champ de bataille : Conduit: Matchmaking' → 'Champ de bataille : Conduit'.

    Découpe sur le DERNIER ': ' (le nom de base peut lui-même contenir ' : ')."""
    return name.rsplit(": ", 1)[0].strip() if ": " in name else name.strip()


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


def collect_portal(activities: list[dict], manifest, portal: dict) -> list[PortalCategory]:
    """Regroupe les activités focus/défi par catégorie du Portail.

    Ordre des catégories = CATEGORIES ; dans une catégorie, alertes d'abord
    puis ordre de l'API. Une catégorie sans activité est conservée (vide)."""
    by_root = {
        int(root): set(hashes)
        for root, hashes in (portal.get("categories") or {}).items()
    }
    alerts = set(portal.get("alerts") or [])

    categories = [PortalCategory(key, label, icon) for key, _, label, icon in CATEGORIES]
    groups: list[dict[str, PortalActivity]] = [{} for _ in CATEGORIES]

    for raw in activities:
        challenges = len(raw.get("challenges", []))
        if not raw.get("isFocusedActivity") and not challenges:
            continue
        ah = raw.get("activityHash")
        idx = next(
            (i for i, (_, root, _, _) in enumerate(CATEGORIES) if ah in by_root.get(root, ())),
            None,
        )
        if idx is None:
            continue

        adef = manifest.resolve(ah, "DestinyActivityDefinition")
        name = base_name(adef.get("displayProperties", {}).get("name", ""))
        if not name:
            continue

        act = groups[idx].get(name)
        if act is None:
            act = PortalActivity(base_name=name, pgcr_image=adef.get("pgcrImage") or None)
            groups[idx][name] = act
        act.activity_hashes.append(ah)
        act.focus_hash = act.focus_hash or focus_item_hash(raw)
        act.is_alert = act.is_alert or ah in alerts
        act.is_challenge = act.is_challenge or challenges > 0

    for cat, group in zip(categories, groups):
        cat.activities = sorted(group.values(), key=lambda a: not a.is_alert)
    return categories
