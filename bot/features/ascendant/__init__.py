# -*- coding: utf-8 -*-
"""Logique PURE de la rotation des Défis ascendants (déterministe).

Le défi ascendant tourne d'un défi par semaine, sur un cycle FIXE de 6 (cf.
constants.DEFIS_ORDRE), calé sur le reset hebdomadaire Bungie (mardi 17:00 UTC).
Tout se déduit d'une unique ANCRE :

    index(now) = floor((now - ANCHOR) / 1 semaine) % len(DEFIS_ORDRE)

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

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.features.ascendant.constants import (
    CONTRAT_VERS_DEFI,
    DEFIS_META,
    DEFIS_ORDRE,
    UPCOMING_COUNT,
)
from bot.utils.logger import log

TOPIC = "ascendant"

# Ancre : mardi 28 Juillet 2026, reset hebdo Bungie à 17:00 UTC, index 0 = premier
# défi de DEFIS_ORDRE (agonarch_abyss). Instant UTC pur → insensible au DST.
ANCHOR: datetime = datetime(2026, 7, 28, 17, 0, 0, tzinfo=timezone.utc)

_WEEK = timedelta(weeks=1)


@dataclass(frozen=True)
class AscendantWindow:
    """Une fenêtre hebdomadaire de défi ascendant."""

    challenge: str      # clé interne (cf. DEFIS_ORDRE / DEFIS_META)
    index: int          # numéro de semaine absolu depuis l'ANCRE (dédup / hash)
    start: datetime     # début (UTC, aware) = reset du mardi
    end: datetime       # fin (UTC, aware) = start + 1 semaine

    @property
    def start_unix(self) -> int:
        return int(self.start.timestamp())

    @property
    def end_unix(self) -> int:
        return int(self.end.timestamp())

    @property
    def meta(self) -> dict:
        return DEFIS_META[self.challenge]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _week_index(now: datetime) -> int:
    """Numéro de semaine absolu écoulé depuis l'ANCRE.

    Peut être négatif avant l'ancre : sans conséquence, le modulo Python reste
    correct (résultat toujours dans [0, len(DEFIS_ORDRE)))."""
    elapsed = (now - ANCHOR).total_seconds()
    return math.floor(elapsed / _WEEK.total_seconds())


def _window_for_week(week_index: int) -> AscendantWindow:
    start = ANCHOR + week_index * _WEEK
    return AscendantWindow(
        challenge=DEFIS_ORDRE[week_index % len(DEFIS_ORDRE)],
        index=week_index,
        start=start,
        end=start + _WEEK,
    )


def current_window(now: datetime | None = None) -> AscendantWindow:
    """Fenêtre de défi ACTIVE à `now` (défaut : maintenant, UTC)."""
    return _window_for_week(_week_index(now or _now()))


def upcoming_windows(
    now: datetime | None = None, count: int = UPCOMING_COUNT
) -> list[AscendantWindow]:
    """Les `count` fenêtres SUIVANTES (après l'active), dans l'ordre."""
    base = _week_index(now or _now())
    return [_window_for_week(base + i) for i in range(1, count + 1)]


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
    cle = win.challenge
    source = "formule"

    if hash_contrat is not None:
        cle_contrat = CONTRAT_VERS_DEFI.get(hash_contrat)
        if cle_contrat is None:
            log.warning(
                f"[Ascendant] Contrat inconnu {hash_contrat} — repli sur la "
                f"formule ({win.challenge})."
            )
        else:
            cle = cle_contrat
            source = "contrat"
            if cle_contrat != win.challenge:
                log.warning(
                    f"[Ascendant] Divergence contrat/formule : contrat="
                    f"{cle_contrat} formule={win.challenge} (le contrat fait foi)."
                )

    return {"cle": cle, "source": source, "window": win, **DEFIS_META[cle]}
