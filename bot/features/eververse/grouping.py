# -*- coding: utf-8 -*-
"""Regroupement des ventes Eververse par section (logique pure, sans I/O réseau).

Reçoit le bloc `sales.data` de GetVendors (pluriel) et renvoie, pour chaque
section de SECTIONS, la liste ordonnée des items bruts (itemHash + coût [+
class_label]) — SANS résolution de nom/icône. Isolé ici pour être testable sans
dépendance réseau (cf. service.py pour l'orchestration + résolution).

Cas particulier — vendor d'ornements d'armure (ARMOR_ORNAMENTS_VENDOR) : son
contenu N'est PAS lu depuis `sales_data` (fetch groupé = perso principal
seulement). Le service le fetch séparément pour les 3 classes et passe la liste
déjà construite (`armor_ornaments`) : grouping l'injecte À LA POSITION du vendor
dans SECTIONS (2e vendor de la section principale), préservant l'ordre voulu."""
from __future__ import annotations

from .constants import ARMOR_ORNAMENTS_VENDOR, SECTIONS


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


def build_raw_sections(
    sales_data: dict, armor_ornaments: list[dict] | None = None
) -> list[dict]:
    """Regroupe les saleItems par section (ordre fixe), sans résolution.

    Retour : [{id, title, currency, items:[{item_hash, cost_quantity,
    class_label}]}].

    `armor_ornaments` : items déjà construits (multi-classe) du vendor
    ARMOR_ORNAMENTS_VENDOR, injectés à la position de ce vendor dans SECTIONS.
    Chaque entrée doit être un dict {item_hash, cost_quantity, class_label}.

    Les vendors absents de `sales_data` sont ignorés silencieusement."""
    armor_ornaments = armor_ornaments or []
    result: list[dict] = []
    for sec in SECTIONS:
        items: list[dict] = []
        for vendor_hash in sec["vendors"]:
            # Vendor d'ornements d'armure : injection multi-classe à sa position.
            if vendor_hash == ARMOR_ORNAMENTS_VENDOR:
                items.extend(armor_ornaments)
                continue
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
                    "class_label": None,
                })
        result.append({
            "id": sec["id"],
            "title": sec["title"],
            "currency": sec["currency"],
            "items": items,
        })
    return result