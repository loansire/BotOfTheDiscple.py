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
from bot.bungie.items import item_display, log_vendor_positions
from bot.core.aio import gather_limited
from bot.core.logger import log

from .constants import ADA_VENDOR_HASH
from .filtering import filtered_items
from .models import AdaItem


async def _resolve_item(item_hash: int, cost_quantity: int | None) -> AdaItem | None:
    """itemHash → AdaItem (icon + watermark + coût), nom FR si disponible."""
    item = await item_display(item_hash)
    if item is None:
        return None
    return AdaItem(
        item_hash=item_hash,
        name=item.name,
        icon=item.icon,
        watermark=item.watermark,
        cost_quantity=cost_quantity,
    )


async def get_ada() -> list[AdaItem]:
    """Inventaire d'Ada-1 : items filtrés par position puis résolus.

    Renvoie une liste (éventuellement vide si les ventes sont indisponibles ou
    si le filtre ne laisse rien). Auth OAuth requise (endpoint vendor)."""
    sales = await bungie.get_vendor_sales(ADA_VENDOR_HASH)
    if not sales:
        log.error("[Ada-1] Ventes indisponibles.")
        return []

    if os.getenv("ADA_DEBUG"):
        await log_vendor_positions("Ada-1", sales)

    resolved = await gather_limited(
        _resolve_item(item_hash, cost_quantity)
        for item_hash, cost_quantity in filtered_items(sales)
    )
    items: list[AdaItem] = [item for item in resolved if item]

    log.info(f"[Ada-1] {len(items)} item(s) retenu(s).")
    return items