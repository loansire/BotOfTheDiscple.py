# -*- coding: utf-8 -*-
"""Récupération LIVE du contrat hebdo de Petra (composant 402 VendorSales).

But : lire l'itemHash du contrat « Défi ascendant » vendu par Petra pour
valider/forcer la résolution du défi de la semaine (cf. ascendant.resolve).

Endpoint (via BungieClient.get_vendor_sales, auth OAuth requise) :
    /Destiny2/{type}/Profile/{membership}/Character/{char}/Vendors/1841717884/
      ?components=402
→ sales.data = { "<index>": { "itemHash": ..., ... } }

On parcourt les cases et on renvoie le 1er itemHash présent dans
CONTRAT_VERS_DEFI (les 6 contrats connus). Petra vend aussi d'autres items
(Teinture de Feuillereine, fragments…) : seul le contrat nous intéresse.

Coût réseau MAÎTRISÉ : mémoïsation par SEMAINE (index d'ancre). Même appelé à
chaque poll/min, le réseau n'est sollicité qu'UNE fois par semaine (plus une
fois au redémarrage). En cas d'échec/maintenance, on N'ÉCHOUE PAS : la formule
déterministe reste la source de vérité — on renvoie None et on marque la semaine
comme tentée (aucun martèlement). Le contrat n'est qu'une couche de validation
/ d'override (cf. resolve : divergence → le contrat fait foi et est logué)."""
from __future__ import annotations

from datetime import datetime, timezone

from bot.bungie.client import bungie
from bot.features.ascendant import current_window
from bot.features.ascendant.constants import CONTRAT_VERS_DEFI
from bot.utils.logger import log

# Vendor Petra Venj (Cité des Rêves).
PETRA_VENDOR_HASH = 1841717884

# Mémo (week_index, contrat_hash|None) : garantit ≤ 1 appel réseau / semaine.
_cache: tuple[int, int | None] | None = None


async def fetch_contrat_hash(now: datetime | None = None) -> int | None:
    """itemHash du contrat Petra de la semaine, ou None si indisponible.

    Mémoïsé par semaine (index d'ancre). None → la résolution retombe sur la
    formule déterministe (comportement sûr)."""
    global _cache
    wk = current_window(now or datetime.now(timezone.utc)).index
    if _cache is not None and _cache[0] == wk:
        return _cache[1]

    contrat = await _pull_contrat()
    _cache = (wk, contrat)  # on mémorise même None → une seule tentative/semaine
    return contrat


def reset_cache() -> None:
    """Force un re-pull au prochain fetch (utilisé par /refresh)."""
    global _cache
    _cache = None


async def _pull_contrat() -> int | None:
    """Appel réseau brut : renvoie l'itemHash du contrat connu, ou None."""
    try:
        sales = await bungie.get_vendor_sales(PETRA_VENDOR_HASH)
    except Exception as e:  # BungieMaintenanceError incluse → repli formule
        log.warning(f"[Ascendant] Pull Petra échoué ({e}) — repli sur la formule.")
        return None

    if not sales:
        log.warning("[Ascendant] Ventes Petra vides/indisponibles — repli formule.")
        return None

    for case in sales.values():
        ih = case.get("itemHash")
        if isinstance(ih, int) and ih in CONTRAT_VERS_DEFI:
            return ih

    log.warning(
        "[Ascendant] Aucun contrat connu dans les ventes Petra — repli formule."
    )
    return None
