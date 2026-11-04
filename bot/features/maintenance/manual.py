# -*- coding: utf-8 -*-
"""Déclaration manuelle d'une maintenance : jour en anglais (« October 20 »),
heures AM/PM avec fuseau (« 8:30 AM PDT ») → timestamps Unix."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone, tzinfo
from functools import cache
from typing import Optional
from zoneinfo import ZoneInfo

from .formatter import GAME_LABELS, format_window_message

# Une date plus de ~6 mois dans le passé est lue comme l'année suivante
# (déclaration en décembre d'une maintenance de janvier).
_PAST_TOLERANCE = timedelta(days=183)

_MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_MONTHS = {name: i for i, name in enumerate(_MONTH_NAMES, 1)}
_MONTHS.update({name[:3]: i for i, name in enumerate(_MONTH_NAMES, 1)})
_MONTHS["sept"] = 9

# PDT/PST : décalage FIXE tel que saisi (le texte de Bungie fait foi). PT :
# Pacific avec gestion automatique de l'heure d'été. Sans fuseau → PT.
_FIXED_ZONES = {
    "PDT": timezone(timedelta(hours=-7)),
    "PST": timezone(timedelta(hours=-8)),
    "UTC": timezone.utc,
    "GMT": timezone.utc,
    "CEST": timezone(timedelta(hours=2)),
    "CET": timezone(timedelta(hours=1)),
}
_NAMED_ZONES = {"PT": "America/Los_Angeles", "PARIS": "Europe/Paris"}
DEFAULT_ZONE = "PT"
ACCEPTED_ZONES = ", ".join(sorted({*_FIXED_ZONES, *_NAMED_ZONES}))

_ORDINAL_RE = re.compile(r"(?<=\d)(?:st|nd|rd|th)\b", re.I)
_DAY_RES = (
    re.compile(r"^(?P<month>[a-z]+)\.?\s+(?P<day>\d{1,2})$", re.I),   # October 20
    re.compile(r"^(?P<day>\d{1,2})\s+(?P<month>[a-z]+)\.?$", re.I),   # 20 October
)
_CLOCK_RE = re.compile(
    r"^(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ampm>[ap]\.?m\.?)?\s*(?P<zone>[a-z]+)?$",
    re.I,
)


class ManualInputError(ValueError):
    """Saisie illisible ; le message est affiché tel quel à l'utilisateur."""


@cache
def _named_zone(key: str) -> ZoneInfo:
    return ZoneInfo(_NAMED_ZONES[key])


def _zone(name: str) -> tzinfo:
    key = name.upper()
    if key in _FIXED_ZONES:
        return _FIXED_ZONES[key]
    if key in _NAMED_ZONES:
        return _named_zone(key)
    raise ManualInputError(f"Fuseau inconnu : `{name}` (acceptés : {ACCEPTED_ZONES}).")


def parse_day(text: str) -> tuple[int, int]:
    """« October 20 », « Oct 20 », « 20th October » → (mois, jour)."""
    cleaned = _ORDINAL_RE.sub("", text.strip().strip(",")).strip()
    for regex in _DAY_RES:
        match = regex.match(cleaned)
        if match:
            month = _MONTHS.get(match["month"].lower())
            if month is None:
                raise ManualInputError(f"Mois inconnu : `{match['month']}` (en anglais, ex. `October 20`).")
            return month, int(match["day"])
    raise ManualInputError(f"Jour illisible : `{text}` (format attendu : `October 20`).")


def parse_clock(text: str) -> tuple[int, int, tzinfo]:
    """« 8:30 AM PDT » → (heure 0-23, minute, fuseau). Sans AM/PM : 24 h."""
    match = _CLOCK_RE.match(text.strip())
    if not match:
        raise ManualInputError(f"Heure illisible : `{text}` (format attendu : `8:30 AM PDT`).")
    hour, minute = int(match["h"]), int(match["m"] or 0)
    ampm = (match["ampm"] or "").lower().replace(".", "")
    if minute > 59:
        raise ManualInputError(f"Minutes invalides dans `{text}`.")
    if ampm:
        if not 1 <= hour <= 12:
            raise ManualInputError(f"Heure invalide dans `{text}` (1 à 12 avec AM/PM).")
        hour = hour % 12 + (12 if ampm == "pm" else 0)
    elif hour > 23:
        raise ManualInputError(f"Heure invalide dans `{text}`.")
    return hour, minute, _zone(match["zone"] or DEFAULT_ZONE)


def _build(day: date, hour: int, minute: int, tz: tzinfo) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)


def parse_window(
    day: str, start: str, end: str, *, now: Optional[datetime] = None
) -> tuple[int, int]:
    """(arrêt, retour) en timestamps Unix. La fin prend le même jour que le
    début, ou le lendemain si elle tombe avant."""
    now = now or datetime.now(timezone.utc)
    month, dom = parse_day(day)
    s_hour, s_min, s_tz = parse_clock(start)
    e_hour, e_min, e_tz = parse_clock(end)

    year = now.astimezone(s_tz).year
    try:
        start_dt = _build(date(year, month, dom), s_hour, s_min, s_tz)
        if start_dt < now - _PAST_TOLERANCE:
            year += 1
            start_dt = _build(date(year, month, dom), s_hour, s_min, s_tz)
        end_dt = _build(date(year, month, dom), e_hour, e_min, e_tz)
        if end_dt <= start_dt:
            end_dt = _build(date(year, month, dom) + timedelta(days=1), e_hour, e_min, e_tz)
    except ValueError:
        raise ManualInputError(f"Date inexistante : `{day}`.") from None
    return int(start_dt.timestamp()), int(end_dt.timestamp())


def build_manual_window(
    game: str, day: str, start: str, end: str, description: Optional[str],
    *, now: Optional[datetime] = None,
) -> dict:
    """Maintenance prête à être stockée / publiée (même forme que
    `extract_window`, plus `source` et `copy_text`)."""
    offline, online = parse_window(day, start, end, now=now)
    comment = (description or "").strip() or None
    return {
        "game": game,
        "game_label": GAME_LABELS.get(game, game.title()),
        "event_type": comment,
        "offline_unix": offline,
        "online_unix": online,
        "source": "manual",
        "copy_text": format_window_message(game, comment, offline, online),
    }
