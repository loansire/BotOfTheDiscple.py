# -*- coding: utf-8 -*-
"""Résolution d'items vendus, partagée par les features vendor (Xûr, Ada-1,
Eververse).

DestinyInventoryItemDefinition n'est PAS dans le cache disque : chaque item est
résolu à la volée via l'API live (get_item_definition, petit cache mémoire),
puis son nom est surchargé en FR depuis l'extrait manifest local
(item_names_fr.json) si une traduction existe (sinon nom EN)."""
from __future__ import annotations

from dataclasses import dataclass

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.bungie.sales import sorted_keys
from bot.core.logger import log


@dataclass(frozen=True)
class ItemDisplay:
    defn: dict              # définition brute (pour les détails propres à la feature)
    name: str               # FR si disponible, sinon EN
    icon: str | None
    watermark: str | None


async def item_display(item_hash: int) -> ItemDisplay | None:
    """Définition + nom/icône/watermark d'un item, ou None si introuvable."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    return ItemDisplay(
        defn=defn,
        name=manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}"),
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
    )


async def log_vendor_positions(tag: str, sales: dict, title: str = "") -> None:
    """Diagnostic : position (1-based) → nom d'item de chaque case, pour régler
    les filtres positionnels sur données réelles (activé par *_DEBUG)."""
    keys = sorted_keys(sales)
    head = f"{title} — " if title else ""
    log.info(f"[{tag}][debug] {head}{len(keys)} case(s) :")
    for rank, k in enumerate(keys, start=1):
        ih = sales[k].get("itemHash")
        name = f"hash={ih}"
        if isinstance(ih, int):
            defn = await bungie.get_item_definition(ih)
            if defn:
                name = defn.get("displayProperties", {}).get("name", name)
        log.info(f"[{tag}][debug]   position {rank} (clé {k}) → {name}")
