# -*- coding: utf-8 -*-
"""Orchestration Table de butin : tables maison → résolution des items → modèles.

API publique de la feature. Ne touche ni à Discord ni au rendu.

Aucune notion de cadence ni de vendor : la source est maintenue à la main en
base (compute_loot_table*), relue périodiquement — l'éditer prend donc effet
sans redémarrer le bot. Le seul I/O réseau est la résolution des définitions d'items
(get_item_definition, qui porte son propre cache mémoire), identique à Xûr et
Eververse : endpoint public, pas d'OAuth.
"""
from __future__ import annotations

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.core.logger import log
from bot.storage.static_data import loot_tables

from .constants import TIER_EXOTIC, activity_type_order
from .models import LootActivity, LootItem

# Style de tooltip signalant une arme au schéma extractible (façonnable /
# « Souvenance »). Volontairement DUPLIQUÉ depuis features/xur/service.py : une
# feature ne doit pas importer les internes d'une autre. Si la logique devait
# évoluer, la remonter dans un module partagé (bot/bungie/items.py) plutôt que
# de faire pointer loottable vers xur.
_DEEPSIGHT_TOOLTIP_STYLE = "ui_display_style_deepsight"


def _load_tables() -> dict:
    """Tables de butin éditées à la main en base (cache mémoire relu
    périodiquement, cf. bot/storage/static_data.py)."""
    return loot_tables()


def _activity_type(entry: dict) -> str | None:
    """Type d'activité normalisé (minuscules, sans espaces), None si absent.

    La normalisation évite qu'un « Prestige » saisi à la main dans le JSON
    passe à côté de la table d'emojis."""
    raw = entry.get("type")
    if not isinstance(raw, str):
        return None
    return raw.strip().casefold() or None


def list_activities() -> list[tuple[str, str, str | None]]:
    """Triplets (clé, libellé, type) de toutes les activités déclarées.

    Tri : type d'activité d'abord (cf. ACTIVITY_TYPE_ORDER), libellé
    alphabétique ensuite. Alimente l'autocomplétion de /loottable."""
    triples = [
        (key, str(entry.get("label") or key), _activity_type(entry))
        for key, entry in _load_tables().items()
    ]
    return sorted(triples, key=lambda t: (activity_type_order(t[2]), t[1].lower()))


def _is_craftable(defn: dict) -> bool:
    """True si la définition porte le tooltip Souvenance (schéma extractible).

    On matche le `displayStyle` (stable, indépendant de la langue), jamais le
    `displayString` EN. Robuste si le champ est absent ou None."""
    for tip in defn.get("tooltipNotifications") or []:
        if tip.get("displayStyle") == _DEEPSIGHT_TOOLTIP_STYLE:
            return True
    return False


async def _resolve_item(item_hash: int) -> LootItem | None:
    """itemHash → LootItem, ou None si la définition est introuvable.

    Le nom vient de l'API live (EN) puis est surchargé en FR si l'extrait
    manifest local (item_names_fr.json) contient une traduction — même stratégie
    que Xûr/Eververse.

    Les caractéristiques d'arme sont lues sous leur forme NUMÉRIQUE :
    `itemSubType` (type d'arme), `defaultDamageType` (élément) et
    `equippingBlock.ammoType` (munitions). Aucune n'est obligatoire : un item
    non-arme (armure, ornement…) sortira simplement sans ces tags."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        log.warning(f"[LootTable] Définition introuvable pour l'item {item_hash}.")
        return None

    display = defn.get("displayProperties", {})
    name = manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}")
    equipping = defn.get("equippingBlock") or {}
    inventory = defn.get("inventory") or {}

    return LootItem(
        item_hash=item_hash,
        name=name,
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
        is_exotic=inventory.get("tierType") == TIER_EXOTIC,
        craftable=_is_craftable(defn),
        sub_type=defn.get("itemSubType"),
        damage_type=defn.get("defaultDamageType"),
        ammo_type=equipping.get("ammoType"),
    )


async def get_loot_table(key: str) -> LootActivity | None:
    """Table de butin d'une activité, ou None si la clé est inconnue.

    L'ordre des items suit celui du JSON (choix éditorial assumé : c'est toi qui
    ordonnes). Les hashes non résolubles sont ignorés avec un warning plutôt que
    de faire échouer toute la commande."""
    entry = _load_tables().get(key)
    if entry is None:
        return None

    activity = LootActivity(
        key=key,
        label=str(entry.get("label") or key),
        banner=entry.get("banner") or None,
        type=_activity_type(entry),
    )

    for raw in entry.get("items") or []:
        try:
            item_hash = int(raw)
        except (TypeError, ValueError):
            log.warning(f"[LootTable] Hash invalide dans « {key} » : {raw!r}")
            continue
        item = await _resolve_item(item_hash)
        if item is not None:
            activity.items.append(item)

    return activity
