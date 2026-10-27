# -*- coding: utf-8 -*-
"""Calcul des resets Bungie (quotidien + hebdo).

Le reset Bungie tombe à 17:00 UTC toute l'année (soit 18h Paris en hiver,
19h en été). On calcule donc en UTC pur : raisonner en heure de Paris obligeait
à deviner le décalage DST, ce qui donnait un reset faux d'une heure les jours de
changement d'heure (et un « nouveau reset » fantôme dans la pipeline).
L'affichage localisé est laissé à Discord (<t:…>).

Module volontairement sans dépendance interne : il est importé à la fois
par le client Bungie (cache profil), la pipeline de reset et les embeds,
sans créer de cycle.
"""
from datetime import datetime, time, timedelta, timezone

# Heure du reset quotidien (UTC).
RESET_TIME_UTC = time(17, 0, tzinfo=timezone.utc)

# Jours de la semaine (Python weekday(): lundi=0 … dimanche=6).
MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = range(7)


def last_reset(now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du dernier reset quotidien survenu (<= now).

    `now` peut être fourni pour les tests ; par défaut, l'instant courant.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    reset_today = datetime.combine(now.date(), RESET_TIME_UTC)

    # Avant le reset du jour → le dernier reset est celui de la veille.
    if now < reset_today:
        reset_today -= timedelta(days=1)
    return reset_today


def next_reset(now: datetime | None = None) -> datetime:
    """Datetime (UTC, aware) du prochain reset quotidien à venir (> now).

    Utilisé pour afficher « prochaine actualisation » des contenus quotidiens
    (secteurs oubliés)."""
    return last_reset(now) + timedelta(days=1)


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


def last_weekday_reset(target_weekday: int, now: datetime | None = None) -> datetime:
    """Dernier reset (<= now) tombant un jour de semaine donné (ex. le dernier
    reset du mardi = début de la semaine Destiny en cours)."""
    return next_weekday_reset(target_weekday, now) - timedelta(days=7)
