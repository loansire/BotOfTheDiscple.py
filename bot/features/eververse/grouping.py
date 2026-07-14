# -*- coding: utf-8 -*-
"""Regroupement des ventes Eververse par section (logique pure, sans I/O réseau).

Reçoit le bloc `sales.data` de GetVendors (pluriel) et renvoie, pour chaque
section de SECTIONS, la liste ordonnée des items bruts (itemHash + coût) — SANS
résolution de nom/icône. Isolé ici pour être testable sans dépendance réseau
(cf. service.py pour l'orchestration + résolution)."""
from __future__ import annotations

from .constants import SECTIONS


def sorted_sale_items(entry: dict) -> list[tuple[str, dict]]:
    """(index, sale) d'un vendor triés par index numérique croissant.

    L'index = la position de la « case » dans l'inventaire du vendor ; on trie
    pour un ordre d'affichage stable, comme pour Xûr."""
    items = entry.get("saleItems", {}) or {}
    return sorted(
        items.items(),
        key=lambda kv: int(kv[0]) if str(kv[0]).isdigit() else 0,
    )


def first_cost_quantity(sale: dict) -> int | None:
    """Quantité du 1er coût d'une case (costs[0].quantity), ou None."""
    costs = sale.get("costs") or []
    if not costs:
        return None
    qty = costs[0].get("quantity")
    return qty if isinstance(qty, int) else None


def build_raw_sections(sales_data: dict) -> list[dict]:
    """Regroupe les saleItems par section (ordre fixe), sans résolution.

    Retour : [{id, title, currency, items:[{item_hash, cost_quantity}]}].
    Les vendors absents de `sales_data` sont ignorés silencieusement."""
    result: list[dict] = []
    for sec in SECTIONS:
        items: list[dict] = []
        for vendor_hash in sec["vendors"]:
            entry = sales_data.get(str(vendor_hash))
            if not entry:
                continue
            for _idx, sale in sorted_sale_items(entry):
                ih = sale.get("itemHash")
                if not isinstance(ih, int):
                    continue
                items.append({
                    "item_hash": ih,
                    "cost_quantity": first_cost_quantity(sale),
                })
        result.append({
            "id": sec["id"],
            "title": sec["title"],
            "currency": sec["currency"],
            "items": items,
        })
    return result