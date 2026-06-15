# -*- coding: utf-8 -*-
"""Orchestration Xûr : fetch des 3 vendors → résolution des items → modèles.

API publique de la feature. Ne touche ni à Discord ni au rendu.

Fenêtre Xûr : présent du vendredi (reset, 17:00 UTC) au mardi (reset). On
calcule tout sur le jour du dernier reset (heure de Paris, via reset.py), pour
rester aligné sur l'affichage FR.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from bot.bungie.client import bungie
from bot.bungie.reset import last_reset
from bot.utils.logger import log

from .constants import FRIDAY, TUESDAY, VENDOR_WHITELIST_PATH, XUR_VENDORS
from .models import XurItem, XurVendor


# ── Fenêtre temporelle ─────────────────────────────────────────────────

def _reset_weekday(now: datetime | None = None) -> int:
    """Jour de la semaine (lundi=0) du dernier reset survenu."""
    return last_reset(now).weekday()


def is_xur_active(now: datetime | None = None) -> bool:
    """True si Xûr est présent (entre le reset du vendredi et celui du mardi).

    Jours actifs (jour du dernier reset) : vendredi, samedi, dimanche, lundi.
    Le mardi au reset, Xûr est parti → inactif."""
    return _reset_weekday(now) in {FRIDAY, 5, 6, 0}


def _next_weekday_reset_unix(target_weekday: int, now: datetime | None = None) -> int:
    """Timestamp unix du prochain reset tombant un jour donné (>= maintenant).

    Si le dernier reset est déjà ce jour-là, renvoie celui de la semaine
    suivante (utile pour 'prochaine arrivée' depuis un mardi/vendredi)."""
    base = last_reset(now)
    days_ahead = (target_weekday - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return int((base + timedelta(days=days_ahead)).timestamp())


def next_arrival_unix(now: datetime | None = None) -> int:
    """Timestamp du prochain vendredi-reset (prochaine arrivée de Xûr)."""
    return _next_weekday_reset_unix(FRIDAY, now)


def next_departure_unix(now: datetime | None = None) -> int:
    """Timestamp du prochain mardi-reset (prochain départ de Xûr)."""
    return _next_weekday_reset_unix(TUESDAY, now)


# ── Résolution de l'inventaire ─────────────────────────────────────────

async def _resolve_item(
    item_hash: int, cost_quantity: int | None, quantity: int = 1
) -> XurItem | None:
    """itemHash → XurItem (icon + watermark + coût) via DestinyInventoryItemDefinition.

    `quantity` = nb d'occurrences du même itemHash parmi les cases retenues."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    return XurItem(
        item_hash=item_hash,
        name=display.get("name", f"Item {item_hash}"),
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
        cost_quantity=cost_quantity,
        quantity=quantity,
    )


def _load_whitelist() -> dict:
    """Charge vendor_whitelist.json. {} si absent/illisible (→ tout garder)."""
    if VENDOR_WHITELIST_PATH.exists():
        try:
            with open(VENDOR_WHITELIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"[Xûr] vendor_whitelist.json illisible : {e}")
    return {}


def _sorted_keys(sales: dict) -> list[str]:
    """Clés de sales.data triées par valeur numérique croissante.

    Cet ordre = l'ordre des « cases » dans l'interface du PNJ. La position
    ordinale (1 = 1ère case) est donc stable même si les clés elles-mêmes
    changent d'une semaine à l'autre."""
    return sorted(sales.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)


def _first_cost_quantity(sale: dict) -> int | None:
    """Quantité du 1er coût d'une case sales.data (costs[0].quantity), ou None.

    Tous les items Xûr ont un coût unique (Éclats/Pièces étranges) : seule la
    valeur nous intéresse, pas la nature de la monnaie."""
    costs = sale.get("costs") or []
    if not costs:
        return None
    qty = costs[0].get("quantity")
    return qty if isinstance(qty, int) else None


def _filtered_items(
    sales: dict, allowed: list | None
) -> list[tuple[int, int | None, int]]:
    """Triplets (itemHash, cost_quantity, count) d'un bloc sales.data, filtrés
    par POSITION (1-based).

    `allowed` = liste de positions de « cases » à conserver (1 = 1ère case) :
        - None  → on garde TOUT (vendor absent de la whitelist)
        - [...]  → on ne garde que ces positions (1-based)
        - []     → on ne garde rien

    Les cases sont ordonnées par clé numérique croissante (cf. _sorted_keys) ;
    on sélectionne ensuite par rang, pas par clé — la case n°6 reste la n°6
    même si sa clé Bungie change. Le filtrage opère AVANT toute résolution :
    on ne résout ni ne télécharge les items écartés.

    Déduplication par itemHash : les occurrences multiples (parmi les cases
    retenues) sont COMPTÉES (`count`) au lieu d'être écartées. Le 1er coût
    rencontré est conservé ; l'ordre de première apparition est préservé."""
    keys = _sorted_keys(sales)

    if allowed is None:
        selected_keys = keys
    else:
        # Positions 1-based → index 0-based ; on ignore les positions hors borne.
        allowed_positions = {int(p) for p in allowed}
        selected_keys = [
            key for rank, key in enumerate(keys, start=1)
            if rank in allowed_positions
        ]

    # itemHash → [cost_quantity, count], dans l'ordre de 1ère apparition.
    agg: dict[int, list] = {}
    for key in selected_keys:
        sale = sales[key]
        ih = sale.get("itemHash")
        if not isinstance(ih, int):
            continue
        if ih in agg:
            agg[ih][1] += 1
        else:
            agg[ih] = [_first_cost_quantity(sale), 1]

    return [(ih, cost, count) for ih, (cost, count) in agg.items()]


async def _log_vendor_indices(key: str, label: str, sales: dict) -> None:
    """Diagnostic : imprime position (1-based) → nom d'item pour aider à
    remplir la whitelist. Activé uniquement si XUR_DEBUG est défini."""
    keys = _sorted_keys(sales)
    log.info(f"[Xûr][debug] {label} ({key}) — {len(keys)} case(s) :")
    for rank, k in enumerate(keys, start=1):
        ih = sales[k].get("itemHash")
        name = f"hash={ih}"
        if isinstance(ih, int):
            defn = await bungie.get_item_definition(ih)
            if defn:
                name = defn.get("displayProperties", {}).get("name", name)
        log.info(f"[Xûr][debug]   position {rank} (clé {k}) → {name}")


async def _build_vendor(
    key: str, vendor_hash: int, label: str, emoji: str, whitelist: dict
) -> XurVendor:
    """Fetch un vendor et résout uniquement ses items whitelistés."""
    vendor = XurVendor(key=key, label=label, emoji=emoji)
    sales = await bungie.get_vendor_sales(vendor_hash)
    if not sales:
        return vendor

    if os.getenv("XUR_DEBUG"):
        await _log_vendor_indices(key, label, sales)

    allowed = whitelist.get(key)  # None si vendor absent → tout garder
    for item_hash, cost_quantity, count in _filtered_items(sales, allowed):
        item = await _resolve_item(item_hash, cost_quantity, count)
        if item:
            vendor.items.append(item)
    return vendor


async def get_xur() -> list[XurVendor]:
    """Inventaire de Xûr : un XurVendor par catégorie (ordre fixe), filtré par
    la whitelist d'index (vendor_whitelist.json).

    Renvoie la liste même si certains vendors sont vides (le rendu gère le
    cas). Liste vide globale uniquement si tout échoue."""
    whitelist = _load_whitelist()
    vendors: list[XurVendor] = []
    for key, (vendor_hash, label, emoji) in XUR_VENDORS.items():
        vendor = await _build_vendor(key, vendor_hash, label, emoji, whitelist)
        vendors.append(vendor)
        log.info(f"[Xûr] {label} : {len(vendor.items)} item(s) retenu(s).")
    return vendors