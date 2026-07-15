# -*- coding: utf-8 -*-
"""Orchestration Ada-1 : fetch sales.data → filtre positionnel → résolution.

API publique de la feature. Ne touche ni à Discord ni au rendu.

Ada-1 est un vendor PERMANENT (Tour), inventaire renouvelé chaque semaine au
reset du MARDI. On récupère ses ventes via l'endpoint vendor SINGULIER (comme
Xûr, auth OAuth requise), on retire par POSITION les premières/dernières cases
(cf. filtering.filtered_items), puis on résout chaque item restant. Le nom est
résolu en anglais via l'API live, puis surchargé en FR depuis l'extrait manifest
local (item_names_fr.json) si disponible.

Hold mode : get_vendor_sales laisse remonter BungieMaintenanceError (503 /
SystemDisabled) → la pipeline la transforme en attente au reset."""
from __future__ import annotations

import os

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.utils.logger import log

from .constants import ADA_VENDOR_HASH
from .filtering import filtered_items, sorted_keys
from .models import AdaItem


async def _resolve_item(item_hash: int, cost_quantity: int | None) -> AdaItem | None:
    """itemHash → AdaItem (icon + watermark + coût) via DestinyInventoryItemDefinition.

    Nom résolu en EN via l'API live, surchargé en FR si l'extrait manifest local
    (item_names_fr.json) contient une traduction (sinon fallback EN)."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    name = manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}")
    return AdaItem(
        item_hash=item_hash,
        name=name,
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
        cost_quantity=cost_quantity,
    )


async def _log_vendor_indices(sales: dict) -> None:
    """Diagnostic (ADA_DEBUG) : position (1-based) → nom d'item, pour vérifier le
    filtre positionnel sur données réelles avant de le figer."""
    keys = sorted_keys(sales)
    log.info(f"[Ada-1][debug] {len(keys)} case(s) :")
    for rank, k in enumerate(keys, start=1):
        ih = sales[k].get("itemHash")
        name = f"hash={ih}"
        if isinstance(ih, int):
            defn = await bungie.get_item_definition(ih)
            if defn:
                name = defn.get("displayProperties", {}).get("name", name)
        log.info(f"[Ada-1][debug]   position {rank} (clé {k}) → {name}")


async def get_ada() -> list[AdaItem]:
    """Inventaire d'Ada-1 : items filtrés par position puis résolus.

    Renvoie une liste (éventuellement vide si les ventes sont indisponibles ou
    si le filtre ne laisse rien). Auth OAuth requise (endpoint vendor)."""
    sales = await bungie.get_vendor_sales(ADA_VENDOR_HASH)
    if not sales:
        log.error("[Ada-1] Ventes indisponibles.")
        return []

    if os.getenv("ADA_DEBUG"):
        await _log_vendor_indices(sales)

    items: list[AdaItem] = []
    for item_hash, cost_quantity in filtered_items(sales):
        item = await _resolve_item(item_hash, cost_quantity)
        if item:
            items.append(item)

    log.info(f"[Ada-1] {len(items)} item(s) retenu(s).")
    return items