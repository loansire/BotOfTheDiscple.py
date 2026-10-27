# -*- coding: utf-8 -*-
"""Lecture des blocs de ventes vendor Bungie (logique PURE, sans I/O).

`sales.data` (GetVendor singulier) et `saleItems` (GetVendors pluriel) sont des
dicts { "<index>": {itemHash, costs, ...} }. L'index = la position de la
« case » dans l'interface du PNJ : trier par index numérique donne l'ordre
d'affichage, et la position ordinale (1 = 1ère case) reste stable même si les
clés changent d'une semaine à l'autre.

Sans dépendance interne : importable par les modules de filtrage testables
sans .env (ada/filtering, eververse/grouping)."""
from __future__ import annotations


def sale_index(key) -> int:
    """Index numérique d'une case (clé non numérique → 0)."""
    return int(key) if str(key).isdigit() else 0


def sorted_keys(sales: dict) -> list[str]:
    """Clés d'un bloc de ventes triées par index croissant."""
    return sorted(sales.keys(), key=sale_index)


def first_cost_quantity(sale: dict) -> int | None:
    """Quantité du 1er coût d'une case (costs[0].quantity), ou None.

    Les vendors suivis ont un coût unique par case (Glimmer, Poussière,
    Pièces étranges…) : seule la quantité nous intéresse."""
    costs = sale.get("costs") or []
    if not costs:
        return None
    qty = costs[0].get("quantity")
    return qty if isinstance(qty, int) else None
