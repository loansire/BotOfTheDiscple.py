# -*- coding: utf-8 -*-
"""Tri des activités du Portail (logique pure, sans I/O réseau).

Une activité est retenue si l'API la marque en focus (`isFocusedActivity`) ou
si elle a des challenges actifs (activités « défi », ex. Berceau du mal), ET si
elle appartient à une catégorie publiée d'après l'extrait Portail du manifest
(cf. ManifestStore.portal).

Défis : les challenges sont lus sur le profil du personnage de référence et
disparaissent une fois le défi accompli, alors que le défi (et son arme) tourne
à la SEMAINE. `remembered` ({activity_hash: focus mémorisé}) permet de réafficher un
défi vu plus tôt dans la semaine (mémorisé par le handler)."""
from __future__ import annotations

from .constants import CATEGORIES, CHALLENGE_ANCHORS, OPS_BONUS_REWARD
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


def challenge_pool(adef: dict) -> tuple[int, list[int]] | None:
    """(objectif, pool de récompenses) du 1er défi ANCRÉ de l'activité (cf.
    CHALLENGE_ANCHORS), ou None. Le pool mêle armes et récompenses génériques :
    le tri par type d'item se fait à la résolution (service)."""
    for challenge in adef.get("challenges", []):
        objective = challenge.get("objectiveHash")
        if objective in CHALLENGE_ANCHORS:
            pool = [
                r.get("itemQuantity", {}).get("itemHash")
                for r in challenge.get("displayRewards", [])
            ]
            return objective, [h for h in pool if h]
    return None


def rotate_challenge(weapons: list[int], anchor: int, weeks: int) -> int | None:
    """Arme de la semaine : l'ancre avance de `weeks` crans dans le pool
    d'armes (cyclique). None si l'ancre n'est plus dans le pool."""
    if anchor not in weapons:
        return None
    return weapons[(weapons.index(anchor) + weeks) % len(weapons)]


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
    groups: list[dict[tuple[str, str], PortalActivity]] = [{} for _ in CATEGORIES]

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

        # Une alerte et le focus du jour peuvent porter le même nom (ex. un
        # champ de bataille) : on les sépare pour ne pas mélanger leurs items.
        # Seules des variantes de difficulté distinctes (Normal / Maîtrise)
        # restent regroupées malgré un statut différent.
        label = variant_label(full_name)
        kind = "grandmaster" if ah in grandmaster else "alert" if ah in alerts else "focus"
        act = groups[idx].get((name, kind))
        if act is None and label:
            act = next(
                (
                    a
                    for (n, _), a in groups[idx].items()
                    if n == name and a.difficulties and label not in a.difficulties
                ),
                None,
            )
        if act is None:
            act = PortalActivity(base_name=name, pgcr_image=pgcr_for(adef, defs))
            groups[idx][(name, kind)] = act
        act.activity_hashes.append(ah)
        act.focus_hash = act.focus_hash or focus_item_hash(raw) or remembered.get(ah)
        act.is_focused = act.is_focused or bool(raw.get("isFocusedActivity"))
        if act.challenge_objective is None and (pool := challenge_pool(adef)):
            act.challenge_objective, act.challenge_pool = pool
        act.is_grandmaster = act.is_grandmaster or ah in grandmaster
        act.is_alert = (act.is_alert or ah in alerts) and not act.is_grandmaster
        if label and label not in _NOT_DIFFICULTY and label not in act.difficulties:
            act.difficulties.append(label)
        act.is_challenge = act.is_challenge or is_challenge
        if is_challenge:
            act.challenge_hashes.append(ah)

    for cat, group in zip(categories, groups):
        cat.activities = sorted(
            group.values(), key=lambda a: (not a.is_grandmaster, not a.is_alert)
        )
    return categories


def challenges_of(categories: list[PortalCategory]) -> dict[int, int]:
    """{activity_hash: item focus mémorisé} de TOUTES les activités défi, à
    mémoriser pour la semaine (le défi tourne à la semaine alors que le profil
    le fait disparaître une fois accompli, y compris sur une activité déjà en
    focus). Le focus n'est retenu que pour une activité hors focus : sinon 0,
    le focus du jour primant. Seuls les hashes portant eux-mêmes le défi sont
    retenus, pas les autres variantes regroupées sous le même nom."""
    return {
        ah: 0 if act.is_focused else (act.focus_hash or 0)
        for cat in categories
        for act in cat.activities
        for ah in act.challenge_hashes
    }
