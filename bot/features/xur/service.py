# -*- coding: utf-8 -*-
"""Orchestration Xûr : fetch des vendors → résolution des items → modèles.

API publique de la feature. Ne touche ni à Discord ni au rendu.

Fenêtre Xûr : présent du vendredi (reset, 17:00 UTC) au mardi (reset). On
calcule tout sur le jour du dernier reset (heure de Paris, via reset.py), pour
rester aligné sur l'affichage FR.

Certaines catégories partagent le même vendor_hash (le vendor « Armes » expose
armes exotiques / armes légendaires / armures légendaires). Le bloc `sales` et
le largeIcon d'un hash donné ne sont fetchés qu'UNE SEULE FOIS puis partagés
entre ses catégories : get_vendor_sales n'a pas de cache, on évite ainsi des
appels réseau redondants.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.bungie.reset import last_reset
from bot.utils.logger import log

from .constants import FRIDAY, TUESDAY, VENDOR_WHITELIST_PATH, XUR_VENDORS
from .models import XurItem, XurPerk, XurVendor

# Garde-fou perks : on ne construit le bloc col 3/4 que pour une ARME (itemType
# 3) de rareté LÉGENDAIRE (tierType 5). Exclut nativement exotiques (tierType 6),
# armures et matériaux — donc conforme à « armes légendaires uniquement ».
_ITEM_TYPE_WEAPON = 3
_TIER_LEGENDARY = 5

# Colonnes 3/4 dans le composant 305 (validé empiriquement sur les armes
# légendaires : intrinsèque=0, canon/chargeur=1/2, traits=3 et 4).
_PERK_COL_INDEXES = (3, 4)


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
    item_hash: int,
    cost_quantity: int | None,
    quantity: int = 1,
    sockets: list | None = None,
) -> XurItem | None:
    """itemHash → XurItem (icon + watermark + coût + perks) via DestinyInventoryItemDefinition.

    Le nom est résolu en anglais via l'API live, puis surchargé en FR si
    l'extrait manifest local (item_names_fr.json) contient une traduction.
    `quantity` = nb d'occurrences du même itemHash parmi les cases retenues.
    `sockets` = liste des sockets du vendor (composant 305) pour cet item, si
    disponible : on en tire les perks col 3/4 UNIQUEMENT pour une arme
    légendaire (cf. garde-fous)."""
    defn = await bungie.get_item_definition(item_hash)
    if defn is None:
        return None
    display = defn.get("displayProperties", {})
    # Source principale = API EN (icon + watermark + nom). Surcouche de
    # traduction : si un nom FR existe dans l'extrait manifest local, il
    # remplace le nom EN ; sinon on garde l'EN (fallback naturel).
    name = manifest.item_name_fr(item_hash) or display.get("name", f"Item {item_hash}")

    # Perks col 3/4 : seulement pour une arme légendaire, et seulement si les
    # sockets du vendor sont fournis. Tout le reste (exotiques, armures,
    # matériaux) → pas de bloc perks.
    perks: list[XurPerk] = []
    if sockets:
        inventory = defn.get("inventory") or {}
        if (
            defn.get("itemType") == _ITEM_TYPE_WEAPON
            and inventory.get("tierType") == _TIER_LEGENDARY
        ):
            perks = _extract_col34_perks(sockets)

    return XurItem(
        item_hash=item_hash,
        name=name,
        icon=display.get("icon") or None,
        watermark=defn.get("iconWatermark") or None,
        cost_quantity=cost_quantity,
        quantity=quantity,
        perks=perks,
    )


def _extract_col34_perks(sockets: list) -> list[XurPerk]:
    """Perks des colonnes 3/4 depuis les sockets (composant 305) d'une arme.

    Prend les index 3 et 4. Garde-fou : on ne renvoie des perks QUE si les DEUX
    positions portent un plug visible ET actif — sinon liste vide. Ça protège
    des layouts atypiques (épée/glaive légendaire) où 3/4 ne seraient pas des
    traits : au pire aucun bloc, jamais un affichage faux ou un crash.

    Le nom FR est résolu via l'extrait manifest local (item_names_fr.json couvre
    aussi les plugs) ; fallback lisible si absent."""
    perks: list[XurPerk] = []
    for idx in _PERK_COL_INDEXES:
        if idx >= len(sockets):
            return []
        socket = sockets[idx]
        plug_hash = socket.get("plugHash")
        if (
            not plug_hash
            or not socket.get("isVisible", False)
            or not socket.get("isEnabled", False)
        ):
            return []
        name = manifest.item_name_fr(plug_hash) or f"Perk {plug_hash}"
        perks.append(XurPerk(plug_hash=plug_hash, name=name))
    return perks


async def _resolve_vendor_large_icon(vendor_hash: int) -> str | None:
    """displayProperties.largeIcon d'un vendor (chemin relatif), ou None.

    Image d'en-tête de la catégorie. Résolue via l'API live (le vendor n'est
    pas dans le cache manifest disque)."""
    defn = await bungie.get_vendor_definition(vendor_hash)
    if defn is None:
        return None
    return (defn.get("displayProperties") or {}).get("largeIcon") or None


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
) -> list[tuple[int, int | None, int, str]]:
    """Quadruplets (itemHash, cost_quantity, count, first_key) d'un bloc
    sales.data, filtrés par POSITION (1-based).

    `allowed` = liste de positions de « cases » à conserver (1 = 1ère case) :
        - None  → on garde TOUT (catégorie absente de la whitelist)
        - [...]  → on ne garde que ces positions (1-based)
        - []     → on ne garde rien

    Les cases sont ordonnées par clé numérique croissante (cf. _sorted_keys) ;
    on sélectionne ensuite par rang, pas par clé — la case n°6 reste la n°6
    même si sa clé Bungie change. Le filtrage opère AVANT toute résolution :
    on ne résout ni ne télécharge les items écartés.

    Déduplication par itemHash : les occurrences multiples (parmi les cases
    retenues) sont COMPTÉES (`count`) au lieu d'être écartées. Le 1er coût
    rencontré est conservé ; l'ordre de première apparition est préservé. La
    `first_key` (clé sales.data de la 1ère occurrence) est renvoyée pour
    retrouver les sockets correspondants (composant 305, même indexation)."""
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

    # itemHash → [cost_quantity, count, first_key], dans l'ordre de 1ère apparition.
    agg: dict[int, list] = {}
    for key in selected_keys:
        sale = sales[key]
        ih = sale.get("itemHash")
        if not isinstance(ih, int):
            continue
        if ih in agg:
            agg[ih][1] += 1
        else:
            agg[ih] = [_first_cost_quantity(sale), 1, key]

    return [
        (ih, cost, count, first_key)
        for ih, (cost, count, first_key) in agg.items()
    ]


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


async def _build_vendor_from_sales(
    key: str,
    vendor_hash: int,
    label: str,
    emoji: str,
    sales: dict | None,
    sockets: dict | None,
    large_icon: str | None,
    whitelist: dict,
) -> XurVendor:
    """Construit un XurVendor depuis un bloc `sales` DÉJÀ fetché.

    Plusieurs catégories peuvent partager le même `sales` (même vendor_hash) :
    chacune est découpée par SA plage de positions (whitelist[key]). Aucun appel
    réseau ici — le fetch (sales + sockets + largeIcon) est mutualisé en amont
    par get_xur. `sockets` (composant 305, même indexation que sales) alimente
    les perks col 3/4 des armes légendaires ; peut être None/{} (autres vendors).
    """
    vendor = XurVendor(key=key, label=label, emoji=emoji, large_icon=large_icon)
    if not sales:
        return vendor

    if os.getenv("XUR_DEBUG"):
        await _log_vendor_indices(key, label, sales)

    allowed = whitelist.get(key)  # None si catégorie absente → tout garder
    for item_hash, cost_quantity, count, first_key in _filtered_items(sales, allowed):
        item_sockets = None
        if sockets:
            entry = sockets.get(first_key) or {}
            item_sockets = entry.get("sockets")
        item = await _resolve_item(item_hash, cost_quantity, count, item_sockets)
        if item:
            vendor.items.append(item)

    # Armes exotiques : la dernière case retenue est en réalité l'item à
    # afficher en tête de la catégorie. On la remonte en première position.
    # (Auparavant appliqué au vendor « weapons » entier ; désormais ciblé sur
    # la sous-catégorie exotique — à ajuster si la position réelle diffère.)
    if key == "exotics-weapons" and len(vendor.items) > 1:
        vendor.items.insert(0, vendor.items.pop())

    return vendor


async def get_xur() -> list[XurVendor]:
    """Inventaire de Xûr : un XurVendor par catégorie (ordre fixe de
    XUR_VENDORS), filtré par la whitelist de positions (vendor_whitelist.json).

    Fetch mutualisé : les catégories partageant un même vendor_hash (le vendor
    Armes → exotiques / légendaires / armures légendaires) réutilisent le même
    bloc `sales` et le même largeIcon, fetchés une seule fois par hash distinct
    (get_vendor_sales n'a pas de cache).

    Renvoie la liste même si certaines catégories sont vides (le rendu gère le
    cas). Liste vide globale uniquement si tout échoue."""
    whitelist = _load_whitelist()
    sales_by_hash: dict[int, dict | None] = {}
    sockets_by_hash: dict[int, dict] = {}
    icon_by_hash: dict[int, str | None] = {}
    vendors: list[XurVendor] = []

    for key, (vendor_hash, label, emoji) in XUR_VENDORS.items():
        # Un seul appel réseau (sales + sockets + largeIcon) par vendor_hash distinct.
        if vendor_hash not in sales_by_hash:
            fetched = await bungie.get_vendor_sales_sockets(vendor_hash)
            if fetched is None:
                sales_by_hash[vendor_hash] = None
                sockets_by_hash[vendor_hash] = {}
            else:
                sales_by_hash[vendor_hash], sockets_by_hash[vendor_hash] = fetched
            icon_by_hash[vendor_hash] = await _resolve_vendor_large_icon(vendor_hash)

        vendor = await _build_vendor_from_sales(
            key,
            vendor_hash,
            label,
            emoji,
            sales_by_hash[vendor_hash],
            sockets_by_hash[vendor_hash],
            icon_by_hash[vendor_hash],
            whitelist,
        )
        vendors.append(vendor)
        log.info(f"[Xûr] {label} : {len(vendor.items)} item(s) retenu(s).")

    return vendors