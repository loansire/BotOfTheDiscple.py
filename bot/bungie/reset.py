# -*- coding: utf-8 -*-
"""Calcul du dernier reset quotidien Bungie.

Le reset Bungie tombe à 17:00 UTC, soit 18h Paris en hiver (CET) et
19h Paris en été (CEST). On raisonne en heure de Paris pour rester aligné
sur l'affichage FR, puis on renvoie un datetime *aware* en UTC.

Module volontairement sans dépendance interne : il est importé à la fois
par le client Bungie (cache profil) et par le futur cog de polling, sans
créer de cycle.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")


def last_reset(now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du dernier reset quotidien survenu (<= now).

    `now` peut être fourni pour les tests ; par défaut, l'instant courant.
    """
    now = now or datetime.now(timezone.utc)
    now_paris = now.astimezone(_PARIS)

    # dst() vaut timedelta(0) en hiver (falsy) et timedelta(1h) en été (truthy)
    reset_hour = 19 if now_paris.dst() else 18
    reset_today = datetime.combine(
        now_paris.date(), time(reset_hour, 0, 0), tzinfo=_PARIS
    )

    # Avant le reset du jour → le dernier reset est celui de la veille.
    if now_paris < reset_today:
        reset_today -= timedelta(days=1)

    return reset_today.astimezone(timezone.utc)