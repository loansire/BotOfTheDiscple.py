# -*- coding: utf-8 -*-
"""Rotation FIXE déterministe, calée sur une ancre (aucun appel réseau).

Une clé par période, sur un cycle d'ordre fixe. Tout se déduit d'une ANCRE :

    index(now) = floor((now - anchor) / période)
    clé        = order[index % len(order)]

Le calcul se fait en temps UTC réellement écoulé, donc insensible au
changement d'heure. Avant l'ancre, l'index est négatif : sans conséquence, le
modulo Python reste dans [0, len(order)).

Utilisé par la Distorsion (1 h) et les Défis ascendants (1 semaine). Si Bungie
change l'ordre ou la phase, seuls `order` ou `anchor` sont à mettre à jour."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RotationWindow:
    """Une fenêtre de la rotation."""

    key: str            # élément actif (cf. FixedRotation.order)
    index: int          # numéro de période absolu depuis l'ancre (dédup / hash)
    start: datetime     # début (UTC, aware)
    end: datetime       # fin (UTC, aware) = start + période

    @property
    def start_unix(self) -> int:
        return int(self.start.timestamp())

    @property
    def end_unix(self) -> int:
        return int(self.end.timestamp())


@dataclass(frozen=True)
class FixedRotation:
    anchor: datetime            # instant UTC pur où order[0] devient actif
    period: timedelta
    order: tuple[str, ...]

    def index(self, now: datetime | None = None) -> int:
        """Numéro de période absolu écoulé depuis l'ancre."""
        now = now or datetime.now(timezone.utc)
        return math.floor((now - self.anchor) / self.period)

    def window(self, index: int) -> RotationWindow:
        start = self.anchor + index * self.period
        return RotationWindow(
            key=self.order[index % len(self.order)],
            index=index,
            start=start,
            end=start + self.period,
        )

    def current(self, now: datetime | None = None) -> RotationWindow:
        """Fenêtre ACTIVE à `now` (défaut : maintenant, UTC)."""
        return self.window(self.index(now))

    def upcoming(self, now: datetime | None = None, count: int | None = None) -> list[RotationWindow]:
        """Les `count` fenêtres SUIVANTES (défaut : le reste du cycle, sans
        doublon), dans l'ordre."""
        if count is None:
            count = len(self.order) - 1
        base = self.index(now)
        return [self.window(base + i) for i in range(1, count + 1)]
