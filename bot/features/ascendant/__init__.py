# -*- coding: utf-8 -*-
"""Logique PURE de la rotation des Défis ascendants (déterministe).

Le défi ascendant tourne d'un défi par semaine, sur un cycle FIXE de 6 (cf.
constants.DEFIS_ORDRE), calé sur le reset hebdomadaire Bungie (mardi 17:00 UTC).
Tout se déduit d'une unique ANCRE (cf. bot/core/rotation.py).

Comme 6 défis = 2 cycles de malédiction de 3 semaines, chaque défi est verrouillé
sur une phase de malédiction fixe (→ position de Petra déductible).

Source de vérité : la FORMULE (toujours disponible, aucun appel réseau). Le
contrat hebdo de Petra (composant 402 VendorSales) peut être fourni en OVERRIDE
de validation via resolve(hash_contrat=...) : s'il diverge de la formule, le
contrat fait foi et la divergence est loguée (dérive d'ancre ou changement
Bungie).

Si Bungie modifie l'ordre ou la phase : mettre à jour DEFIS_ORDRE (constants.py)
ou ANCHOR (ci-dessous). La logique, elle, ne change pas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.core.logger import log
from bot.core.rotation import FixedRotation, RotationWindow
from bot.features.ascendant.constants import (
    CONTRAT_VERS_DEFI,
    DEFIS_META,
    DEFIS_ORDRE,
)

TOPIC = "ascendant"

# Ancre : mardi 28 Juillet 2026, reset hebdo Bungie à 17:00 UTC, index 0 = premier
# défi de DEFIS_ORDRE (agonarch_abyss). Instant UTC pur → insensible au DST.
ANCHOR: datetime = datetime(2026, 7, 28, 17, 0, 0, tzinfo=timezone.utc)

ROTATION = FixedRotation(ANCHOR, timedelta(weeks=1), DEFIS_ORDRE)

# Fenêtre hebdomadaire : `key` = clé du défi (cf. DEFIS_META).
AscendantWindow = RotationWindow


def current_window(now: datetime | None = None) -> RotationWindow:
    """Fenêtre de défi ACTIVE à `now` (défaut : maintenant, UTC)."""
    return ROTATION.current(now)


def upcoming_windows(now: datetime | None = None, count: int | None = None) -> list[RotationWindow]:
    """Les `count` fenêtres SUIVANTES (défaut : cycle complet sans doublon)."""
    return ROTATION.upcoming(now, count)


# Divergences déjà loguées : resolve() est appelé à chaque tick de la boucle
# (calcul du content_hash), on ne logue donc chaque cas qu'une fois.
_logged: set[tuple] = set()


def _warn_once(key: tuple, message: str) -> None:
    if key not in _logged:
        _logged.add(key)
        log.warning(message)


def resolve(hash_contrat: int | None = None, now: datetime | None = None) -> dict:
    """Résout le défi de la semaine.

    Priorité au contrat live (composant 402) si fourni ET connu ; sinon repli
    sur la formule déterministe. Toute divergence ou tout hash inconnu est logué.

    Renvoie DEFIS_META[clé] enrichi de :
      - "cle"    : clé interne du défi résolu
      - "source" : "contrat" | "formule"
      - "window" : la AscendantWindow de la semaine (timing = formule)
    """
    win = current_window(now)
    cle = win.key
    source = "formule"

    if hash_contrat is not None:
        cle_contrat = CONTRAT_VERS_DEFI.get(hash_contrat)
        if cle_contrat is None:
            _warn_once(
                ("inconnu", hash_contrat),
                f"[Ascendant] Contrat inconnu {hash_contrat} — repli sur la "
                f"formule ({win.key}).",
            )
        else:
            cle = cle_contrat
            source = "contrat"
            if cle_contrat != win.key:
                _warn_once(
                    ("divergence", cle_contrat, win.key),
                    f"[Ascendant] Divergence contrat/formule : contrat="
                    f"{cle_contrat} formule={win.key} (le contrat fait foi).",
                )

    return {"cle": cle, "source": source, "window": win, **DEFIS_META[cle]}
