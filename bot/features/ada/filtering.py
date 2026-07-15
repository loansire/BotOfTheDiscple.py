# -*- coding: utf-8 -*-
"""Filtrage positionnel des ventes Ada-1 (logique pure, sans I/O réseau).

Reçoit le bloc `sales.data` de GetVendor (SINGULIER, comme Xûr) et renvoie la
liste ordonnée des items retenus (itemHash + coût), APRÈS retrait des premières
et dernières cases (cf. ADA_SKIP_LEADING / ADA_SKIP_TRAILING). Isolé ici pour
être testable sans dépendance réseau ni .env (cf. service.py pour
l'orchestration + résolution), comme eververse/grouping.py."""
from __future__ import annotations

from .constants import ADA_SKIP_LEADING, ADA_SKIP_TRAILING


def sorted_keys(sales: dict) -> list[str]:
    """Clés de sales.data triées par valeur numérique croissante.

    Cet ordre = l'ordre des « cases » dans l'interface du PNJ ; la position
    ordinale (1 = 1ère case) est donc stable même si les clés changent d'une
    semaine à l'autre."""
    return sorted(sales.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)


def first_cost_quantity(sale: dict) -> int | None:
    """Quantité du 1er coût d'une case (costs[0].quantity), ou None.

    Ada-1 vend contre du Glimmer : seule la quantité nous intéresse."""
    costs = sale.get("costs") or []
    if not costs:
        return None
    qty = costs[0].get("quantity")
    return qty if isinstance(qty, int) else None


def filtered_items(sales: dict) -> list[tuple[int, int | None]]:
    """(itemHash, cost_quantity) des cases retenues, filtrées par POSITION.

    On retire les `ADA_SKIP_LEADING` premières cases et les `ADA_SKIP_TRAILING`
    dernières (cases triées par index croissant). Demande actuelle : positions
    1/2/3 et la dernière ignorées. Le filtrage opère AVANT toute résolution : on
    ne résout ni ne télécharge les items écartés.

    Garde-fou : liste vide si trop peu de cases (≤ leading + trailing), pour
    éviter tout index négatif / résultat incohérent.

    Les itemHash non entiers sont ignorés (mais comptent dans les positions :
    une case vide reste une case)."""
    keys = sorted_keys(sales)
    if len(keys) <= ADA_SKIP_LEADING + ADA_SKIP_TRAILING:
        return []

    kept = keys[ADA_SKIP_LEADING: len(keys) - ADA_SKIP_TRAILING]

    result: list[tuple[int, int | None]] = []
    for key in kept:
        sale = sales[key]
        ih = sale.get("itemHash")
        if not isinstance(ih, int):
            continue
        result.append((ih, first_cost_quantity(sale)))
    return result