# -*- coding: utf-8 -*-
"""Orchestration : manifest.sync → fetch profil → tri → résolution des items focus.

Réutilise le fetch profil (components=204, cache aligné sur le reset
quotidien) de la feature weekly."""
from __future__ import annotations

from datetime import datetime

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.bungie.reset import TUESDAY, last_weekday_reset
from bot.core.logger import log

from .constants import CHALLENGE_ANCHORS, CHALLENGE_REFERENCE_WEEK
from .filters import collect_portal, rotate_challenge
from .models import FocusItem, PortalCategory


async def armor_set(defn: dict) -> tuple[str | None, list[tuple[int, str, int]]]:
    """(nom du set, [(nb de pièces, nom du bonus, sandboxPerkHash)]) d'une
    pièce d'armure, via DestinyEquipableItemSetDefinition (API live, FR)."""
    set_hash = (defn.get("equippingBlock") or {}).get("equipableItemSetHash")
    if not set_hash:
        return None, []
    set_def = await bungie.get_definition_fr("DestinyEquipableItemSetDefinition", set_hash)
    if not set_def:
        return None, []
    perks = []
    for p in set_def.get("setPerks", []):
        perk_hash = p.get("sandboxPerkHash")
        perk = await bungie.get_definition_fr("DestinySandboxPerkDefinition", perk_hash) or {}
        name = perk.get("displayProperties", {}).get("name") or str(perk_hash)
        perks.append((p.get("requiredSetCount", 0), name, perk_hash))
    return set_def.get("displayProperties", {}).get("name"), perks


async def _resolve_focus(item_hash: int) -> FocusItem | None:
    """itemHash → FocusItem via DestinyInventoryItemDefinition (API live),
    nom surchargé en FR via l'extrait manifest local."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    set_name, set_perks = await armor_set(defn)
    return FocusItem(
        set_name=set_name,
        set_perks=set_perks,
        item_hash=item_hash,
        name=manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}"),
        sub_type=defn.get("itemSubType"),
        damage_type=defn.get("defaultDamageType"),
        ammo_type=(defn.get("equippingBlock") or {}).get("ammoType"),
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
    )


# DestinyItemType : arme.
_WEAPON = 3


async def _challenge_weapon(objective: int, pool: list[int], now: datetime | None) -> int | None:
    """Arme de défi de la semaine : pool réduit aux ARMES (type résolu via
    l'API), puis rotation hebdomadaire depuis l'ancre de l'objectif."""
    weapons = []
    for item_hash in pool:
        defn = await bungie.get_item_definition(item_hash)
        if defn and defn.get("itemType") == _WEAPON:
            weapons.append(item_hash)
    weeks = (last_weekday_reset(TUESDAY, now) - CHALLENGE_REFERENCE_WEEK).days // 7
    weapon = rotate_challenge(weapons, CHALLENGE_ANCHORS[objective], weeks)
    if weapon is None:
        log.warning(f"[Avant-garde] Ancre de défi {objective} absente du pool — ancrage à revoir.")
    return weapon


async def get_portal(remembered: dict[int, int] | None = None) -> list[PortalCategory]:
    """Catégories du Portail avec leurs activités du jour (focus résolus).

    `remembered` : défis de la semaine déjà vus ({activity_hash: focus mémorisé}),
    cf. filters.collect_portal. Renvoie [] si le profil ou l'extrait Portail
    est indisponible."""
    await manifest.sync()
    await manifest.preload("DestinyActivityDefinition")
    portal = manifest.portal()
    if not portal.get("categories"):
        log.error("[Avant-garde] Extrait Portail du manifest indisponible.")
        return []

    data = await bungie.get_character_activities()
    if not data:
        log.error("[Avant-garde] Profil personnage indisponible.")
        return []
    block = data.get("activities", {}).get("data", {})

    categories = collect_portal(
        block.get("availableActivities", []), manifest, portal, remembered
    )
    for cat in categories:
        for act in cat.activities:
            if act.focus_hash:
                act.focus = await _resolve_focus(act.focus_hash)
            if act.is_challenge and not act.challenge_objective:
                log.warning(
                    f"[Avant-garde] Défi sans ancre pour « {act.base_name} » "
                    f"(hashes {act.activity_hashes}) — ajouter l'objectif à CHALLENGE_ANCHORS."
                )
            if act.is_challenge and act.challenge_objective:
                weapon = await _challenge_weapon(act.challenge_objective, act.challenge_pool, None)
                if weapon:
                    act.challenge = await _resolve_focus(weapon)
        log.debug(
            f"[Avant-garde] {cat.label} : "
            f"{[(a.base_name, a.focus and a.focus.name, a.challenge and a.challenge.name) for a in cat.activities]}"
        )
    return categories
