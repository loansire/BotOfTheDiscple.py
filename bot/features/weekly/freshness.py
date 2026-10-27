# -*- coding: utf-8 -*-
"""Garde-fou « données pas prêtes », partagé par les topics weekly/daily
(secteurs oubliés, raids, donjons, Avant-garde).

Juste après un reset, Bungie sert parfois encore les données de la période
précédente, ou des activités sans challenges actifs. Publier à ce moment
figerait un contenu faux (avec ping) pour toute la période. En mode `strict`
(pipeline au reset), on lève donc BungieNotReadyError (→ hold mode, nouvelle
tentative) quand :
- rien n'est détecté ;
- le contenu est identique à celui de la période précédente.
Passé STALE_GRACE après le début de période, on publie quand même (avec un
warning) : une vraie répétition d'une période à l'autre reste possible.

La période d'un topic se déduit de son préfixe : `daily_*` → reset quotidien,
sinon → reset hebdo du mardi. Les signatures vivent dans WeeklyMessageState."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.bungie.client import bungie
from bot.bungie.errors import BungieNotReadyError
from bot.bungie.reset import TUESDAY, last_reset, last_weekday_reset
from bot.core.logger import log

# Délai après le début de période au-delà duquel un contenu « suspect » est
# publié quand même.
STALE_GRACE = timedelta(hours=2)


def period_start(topic: str) -> datetime:
    """Début de la période d'un topic (reset quotidien ou reset du mardi)."""
    return last_reset() if topic.startswith("daily_") else last_weekday_reset(TUESDAY)


def not_ready(topic: str, reason: str) -> None:
    """Lève BungieNotReadyError tant que STALE_GRACE n'est pas écoulé, sinon
    logue et laisse publier. Le cache profil est oublié pour que la nouvelle
    tentative refasse un vrai appel API."""
    if datetime.now(timezone.utc) - period_start(topic) >= STALE_GRACE:
        log.warning(f"[Fraîcheur] {topic} : {reason} — délai de grâce écoulé, publication quand même.")
        return
    bungie.invalidate_character_cache()
    raise BungieNotReadyError(f"{topic} : {reason}")


def check_fresh(state, topic: str, sig: list[str]) -> None:
    """Refuse un contenu identique à celui de la période PRÉCÉDENTE."""
    prev = state.last_signature(topic)
    if not prev or prev.get("period") == period_start(topic).isoformat():
        return  # première publication connue, ou période déjà validée
    if prev.get("sig") == sorted(sig):
        not_ready(topic, "contenu identique à la période précédente (données périmées ?)")


def remember(state, topic: str, sig: list[str]) -> None:
    """Mémorise le contenu publié pour la période en cours."""
    state.set_signature(topic, period_start(topic).isoformat(), sig)
