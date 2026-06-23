# -*- coding: utf-8 -*-
"""Calcul des resets Bungie (quotidien + hebdo) — heure de Paris.

Le reset Bungie tombe à 17:00 UTC, soit 18h Paris en hiver (CET) et
19h Paris en été (CEST). On raisonne en heure de Paris pour rester aligné
sur l'affichage FR, puis on renvoie un datetime *aware* en UTC.

Module volontairement sans dépendance interne : il est importé à la fois
par le client Bungie (cache profil), la pipeline de reset et les embeds,
sans créer de cycle.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")

# Jours de la semaine (Python weekday(): lundi=0 … dimanche=6).
MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)


def _reset_hour(dt_paris: datetime) -> int:
    """Heure du reset en local : 18h en hiver (CET), 19h en été (CEST).

    dst() vaut timedelta(0) en hiver (falsy) et timedelta(1h) en été (truthy)."""
    return 19 if dt_paris.dst() else 18


def last_reset(now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du dernier reset quotidien survenu (<= now).

    `now` peut être fourni pour les tests ; par défaut, l'instant courant.
    """
    now = now or datetime.now(timezone.utc)
    now_paris = now.astimezone(_PARIS)

    reset_today = datetime.combine(
        now_paris.date(), time(_reset_hour(now_paris), 0, 0), tzinfo=_PARIS
    )

    # Avant le reset du jour → le dernier reset est celui de la veille.
    if now_paris < reset_today:
        reset_today -= timedelta(days=1)

    return reset_today.astimezone(timezone.utc)


def next_reset(now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du prochain reset quotidien à venir (> now).

    Miroir de last_reset. Utilisé pour afficher « prochaine actualisation »
    des contenus quotidiens (secteurs oubliés)."""
    now = now or datetime.now(timezone.utc)
    now_paris = now.astimezone(_PARIS)

    reset_today = datetime.combine(
        now_paris.date(), time(_reset_hour(now_paris), 0, 0), tzinfo=_PARIS
    )

    # Au reset du jour ou après → le prochain est celui du lendemain.
    if now_paris >= reset_today:
        reset_today += timedelta(days=1)

    return reset_today.astimezone(timezone.utc)


def next_weekday_reset(target_weekday: int, now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du prochain reset tombant un jour de semaine donné.

    Si le dernier reset est déjà ce jour-là, renvoie celui de la semaine
    suivante (cohérent avec « prochaine arrivée/départ » depuis ce jour-là).
    Utilisé pour le contenu hebdomadaire (raids/donjons → mardi) et Xûr."""
    base = last_reset(now)
    days_ahead = (target_weekday - base.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base + timedelta(days=days_ahead)