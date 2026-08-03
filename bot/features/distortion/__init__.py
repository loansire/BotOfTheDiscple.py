# -*- coding: utf-8 -*-
"""Logique PURE de la rotation Distorsion (aucun appel réseau).

La distorsion tourne d'une destination par heure, sur un cycle fixe de 7
(cf. constants.ORDER). Tout se déduit d'une unique ANCRE :

    index(now) = floor((now - ANCHOR) / 1h) % len(ORDER)

Le calcul est fait en heures RÉELLES écoulées (UTC), donc robuste au changement
d'heure. Aucun état « disto active » n'est persisté : c'est recalculable à tout
instant. Seul l'état des messages Discord est persisté (cf. state.py).

Si Bungie change l'ordre ou la phase de la rotation, il suffit de mettre à jour
ORDER (constants.py) ou ANCHOR (ci-dessous) : la logique ne change pas."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from bot.features.distortion.constants import ORDER, UPCOMING_COUNT

TOPIC = "distortion"

# Ancre : dim. 2 août 2026 19:00 Europe/Paris (= 17:00 UTC), index 0 = première
# destination de ORDER. Instant UTC pur → insensible au changement d'heure.
ANCHOR: datetime = datetime(2026, 8, 2, 17, 0, 0, tzinfo=timezone.utc)

_HOUR = timedelta(hours=1)


@dataclass(frozen=True)
class DistortionWindow:
    """Une fenêtre horaire de distorsion."""

    destination: str
    index: int          # numéro d'heure absolu depuis l'ANCRE (dédup / hash)
    start: datetime     # début (UTC, aware)
    end: datetime       # fin (UTC, aware) = start + 1h

    @property
    def start_unix(self) -> int:
        return int(self.start.timestamp())

    @property
    def end_unix(self) -> int:
        return int(self.end.timestamp())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hour_index(now: datetime) -> int:
    """Numéro d'heure absolu écoulé depuis l'ANCRE.

    Peut être négatif avant l'ancre : sans conséquence, le modulo Python reste
    correct (résultat toujours dans [0, len(ORDER))." """
    elapsed = (now - ANCHOR).total_seconds()
    return math.floor(elapsed / 3600)


def _window_for_hour(hour_index: int) -> DistortionWindow:
    start = ANCHOR + hour_index * _HOUR
    return DistortionWindow(
        destination=ORDER[hour_index % len(ORDER)],
        index=hour_index,
        start=start,
        end=start + _HOUR,
    )


def current_window(now: datetime | None = None) -> DistortionWindow:
    """Fenêtre de distorsion ACTIVE à `now` (défaut : maintenant, UTC)."""
    return _window_for_hour(_hour_index(now or _now()))


def upcoming_windows(
    now: datetime | None = None, count: int = UPCOMING_COUNT
) -> list[DistortionWindow]:
    """Les `count` fenêtres SUIVANTES (après l'active), dans l'ordre."""
    base = _hour_index(now or _now())
    return [_window_for_hour(base + i) for i in range(1, count + 1)]
