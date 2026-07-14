# -*- coding: utf-8 -*-
"""Orchestration Eververse : GetVendors (pluriel) → regroupement → résolution.

API publique de la feature. Ne touche ni à Discord ni au rendu : renvoie 3
`EververseSection` prêtes à être présentées (rendu au Lot 2).

Comme Xûr, DestinyInventoryItemDefinition n'est PAS dans le cache disque : on
résout chaque item à la volée via l'API live (get_item_definition, avec petit
cache mémoire), puis on surcharge le nom en FR depuis l'extrait manifest local
(item_names_fr.json) si disponible.

Endpoint pluriel (get_all_vendor_sales) : tous les vendors d'un coup, contre un
appel par vendor pour Xûr. Auth OAuth requise (même contrainte que Xûr)."""
from __future__ import annotations

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.utils.logger import log

from .grouping import build_raw_sections
from .models import EververseItem, EververseSection


async def _resolve_item(
    item_hash: int, cost_quantity: int | None, currency: str
) -> EververseItem | None:
    """itemHash → EververseItem (icon + watermark + coût), nom FR surchargé."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    name = manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}")
    return EververseItem(
        item_hash=item_hash,
        name=name,
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
        cost_quantity=cost_quantity,
        currency=currency,
    )


async def get_eververse() -> list[EververseSection]:
    """Les 3 sections Eververse (ordre fixe), items résolus.

    Renvoie une liste vide si les vendors sont totalement indisponibles. Une
    section sans item est renvoyée vide (le rendu gère le cas)."""
    sales = await bungie.get_all_vendor_sales()
    if not sales:
        log.error("[Eververse] Vendors indisponibles.")
        return []

    sections: list[EververseSection] = []
    for raw in build_raw_sections(sales):
        items: list[EververseItem] = []
        for ri in raw["items"]:
            item = await _resolve_item(
                ri["item_hash"], ri["cost_quantity"], raw["currency"]
            )
            if item:
                items.append(item)
        sections.append(EververseSection(
            id=raw["id"],
            title=raw["title"],
            currency=raw["currency"],
            items=items,
        ))
        log.info(f"[Eververse] {raw['title']} : {len(items)} item(s) résolu(s).")
    return sections