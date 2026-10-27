# -*- coding: utf-8 -*-
"""Logique PURE de la rotation Distorsion (aucun appel réseau).

La distorsion tourne d'une destination par heure, sur un cycle fixe de 7
(cf. constants.ORDER), calé sur une unique ANCRE (cf. bot/core/rotation.py).
Aucun état « disto active » n'est persisté : c'est recalculable à tout instant.
Seul l'état des messages Discord est persisté (cf. state.py).

Si Bungie change l'ordre ou la phase de la rotation, il suffit de mettre à jour
ORDER (constants.py) ou ANCHOR (ci-dessous) : la logique ne change pas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.core.rotation import FixedRotation, RotationWindow
from bot.features.distortion.constants import ORDER

TOPIC = "distortion"

# Ancre : dim. 2 août 2026 19:00 Europe/Paris (= 17:00 UTC), index 0 = première
# destination de ORDER. Instant UTC pur → insensible au changement d'heure.
ANCHOR: datetime = datetime(2026, 8, 2, 17, 0, 0, tzinfo=timezone.utc)

ROTATION = FixedRotation(ANCHOR, timedelta(hours=1), ORDER)

# Fenêtre horaire : `key` = destination active.
DistortionWindow = RotationWindow


def current_window(now: datetime | None = None) -> RotationWindow:
    """Fenêtre de distorsion ACTIVE à `now` (défaut : maintenant, UTC)."""
    return ROTATION.current(now)


def upcoming_windows(now: datetime | None = None, count: int | None = None) -> list[RotationWindow]:
    """Les `count` fenêtres SUIVANTES (défaut : cycle complet sans doublon)."""
    return ROTATION.upcoming(now, count)
