# -*- coding: utf-8 -*-
"""Orchestration Eververse : GetVendors (pluriel) → regroupement → résolution.

API publique de la feature. Ne touche ni à Discord ni au rendu : renvoie les
`EververseSection` prêtes à être présentées.

Comme Xûr, DestinyInventoryItemDefinition n'est PAS dans le cache disque : on
résout chaque item à la volée via l'API live (get_item_definition, avec petit
cache mémoire), puis on surcharge le nom en FR depuis l'extrait manifest local
(item_names_fr.json) si disponible.

Endpoint pluriel (get_all_vendor_sales) : tous les vendors d'un coup, contre un
appel par vendor pour Xûr. Auth OAuth requise (même contrainte que Xûr).

Vendor d'ornements d'armure (ARMOR_ORNAMENTS_VENDOR) : inventaire spécifique à
la classe → interrogé séparément via l'endpoint SINGULIER (get_vendor_sales),
une fois par personnage (Titan / Arcaniste / Chasseur). Les items obtenus sont
taggés d'un `class_label` (affiché au-dessus du coût) et injectés à la position
du vendor par grouping."""
from __future__ import annotations

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest
from bot.config import BUNGIE_CHARACTER_ID, BUNGIE_HUNTER_ID, BUNGIE_WARLOCK_ID
from bot.utils.logger import log

from .constants import ARMOR_ORNAMENT_CLASSES, ARMOR_ORNAMENTS_VENDOR
from .grouping import build_raw_sections, first_cost_quantity, sorted_sale_items
from .models import EververseItem, EververseSection

# Clé de classe (cf. ARMOR_ORNAMENT_CLASSES) → character_id du .env.
_CLASS_CHARACTER_IDS: dict[str, str | None] = {
    "main": BUNGIE_CHARACTER_ID,
    "warlock": BUNGIE_WARLOCK_ID,
    "hunter": BUNGIE_HUNTER_ID,
}


async def _resolve_item(
    item_hash: int,
    cost_quantity: int | None,
    currency: str,
    class_label: str | None = None,
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
        class_label=class_label,
    )


def _sorted_keys(sales: dict) -> list[str]:
    """Clés de sales.data (endpoint singulier) triées par index croissant."""
    return sorted(sales.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)


async def _fetch_armor_ornaments() -> list[dict]:
    """Ornements d'armure des 3 classes → liste de dicts bruts pour grouping.

    Fetch le vendor ARMOR_ORNAMENTS_VENDOR une fois PAR personnage (endpoint
    singulier, shape { "<index>": {itemHash, costs} } comme Xûr). Ordre de
    sortie : par CASE d'abord, puis par CLASSE (Titan → Arcaniste → Chasseur) —
    donc chaque case affiche ses 3 variantes de classe à la suite.

    Une classe dont le character_id est absent du .env est sautée (warning)."""
    # Fetch de chaque classe (dans l'ordre déclaré).
    class_sales: list[tuple[str, dict]] = []
    for key, label in ARMOR_ORNAMENT_CLASSES:
        char_id = _CLASS_CHARACTER_IDS.get(key)
        if not char_id:
            log.warning(
                f"[Eververse] character_id manquant pour la classe '{key}' "
                f"({label}) — classe sautée."
            )
            continue
        sales = await bungie.get_vendor_sales(ARMOR_ORNAMENTS_VENDOR, char_id)
        class_sales.append((label, sales or {}))

    if not class_sales:
        return []

    # Union ordonnée des index de case (toutes classes confondues).
    all_keys: list[str] = []
    seen: set[str] = set()
    for _label, sales in class_sales:
        for k in _sorted_keys(sales):
            if k not in seen:
                seen.add(k)
                all_keys.append(k)
    all_keys.sort(key=lambda k: int(k) if str(k).isdigit() else 0)

    # Case-major, classe-minor : case1(Titan, Arcaniste, Chasseur), case2(...)…
    result: list[dict] = []
    for k in all_keys:
        for label, sales in class_sales:
            sale = sales.get(k)
            if not sale:
                continue
            ih = sale.get("itemHash")
            if not isinstance(ih, int):
                continue
            result.append({
                "item_hash": ih,
                "cost_quantity": first_cost_quantity(sale),
                "class_label": label,
            })
    log.info(f"[Eververse] Ornements d'armure : {len(result)} item(s) multi-classe.")
    return result


async def get_eververse() -> list[EververseSection]:
    """Les sections Eververse (ordre fixe), items résolus.

    Renvoie une liste vide si les vendors sont totalement indisponibles. Une
    section sans item est renvoyée vide (le rendu gère le cas)."""
    sales = await bungie.get_all_vendor_sales()
    if not sales:
        log.error("[Eververse] Vendors indisponibles.")
        return []

    # Ornements d'armure multi-classe (endpoint singulier, 1 appel/perso).
    armor_ornaments = await _fetch_armor_ornaments()

    sections: list[EververseSection] = []
    for raw in build_raw_sections(sales, armor_ornaments):
        items: list[EververseItem] = []
        for ri in raw["items"]:
            item = await _resolve_item(
                ri["item_hash"], ri["cost_quantity"], raw["currency"],
                ri.get("class_label"),
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