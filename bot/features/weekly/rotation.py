# -*- coding: utf-8 -*-
"""Rotation prédictive des raids & donjons hebdomadaires.

Logique PURE : aucun appel réseau, aucune dépendance Discord. À partir des
activités *featured* de la semaine (celles déjà publiées par la feature weekly,
issues de l'API), on retrouve la position de chaque slot dans la séquence
canonique, puis on déroule un cycle complet.

Ancrage : on ré-ancre à CHAQUE appel sur les données API de la semaine en
cours, pour que la prédiction se recale d'elle-même si Bungie décale la
séquence (extension, hotfix, semaine exceptionnelle).

Semaine de RÉFÉRENCE : une semaine observée (slots connus) sert uniquement de
filet de sécurité, quand l'API ne donne pas assez d'ancres :
- un seul slot reconnu → le second est complété depuis la référence, à
  condition que le slot reconnu soit cohérent avec elle ;
- aucun slot reconnu (nom inconnu, renommage manifest) → prédiction depuis la
  référence seule, signalée comme telle.
Un nom featured absent de la séquence n'invalide plus toute la prédiction : il
est remonté à part (« hors cycle ») pour être affiché et logué.

Les libellés des séquences sont exactement ceux des tables d'emotes (cf.
bot/render/activity_emojis.py) : l'emote est donc toujours résolue, et un seul
endroit à éditer quand une activité entre dans la rotation.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from bot.bungie.reset import TUESDAY, last_weekday_reset

# ── Séquences canoniques ───────────────────────────────────────────────
# Les DEUX slots (A / B) parcourent la MÊME séquence avec un décalage
# constant, en avançant d'un cran par semaine. Un cycle complet dure donc
# len(sequence) semaines. Les activités PERMANENTES (Désert Perpétuel,
# Équilibre) n'en font pas partie et sont exclues en amont par l'appelant.
# Vérifié contre la rotation réelle du 29/09 au 27/10/2026.

RAID_SEQUENCE: tuple[str, ...] = (
    "Dernier Vœu",
    "Jardin du Salut",
    "Crypte de la Pierre",
    "Caveau de verre",
    "Serment du Disciple",
    "Chute du Roi",
    "Origine des Cauchemars",
    "Chute de Cropta",
    "Orée du Salut",
)

DUNGEON_SEQUENCE: tuple[str, ...] = (
    "Trône Brisé",
    "Fosse de l'Hérésie",
    "Prophétie",
    "Étreinte de l'Avarice",
    "Dualité",
    "Flèche de la Vigie",
    "Fantômes des Profondeurs",
    "Ruine de la Guerrière",
    "Hôte Vesper",
    "Dogme fragmenté",
)

# Autres noms possibles d'une entrée (traductions concurrentes, renommage
# manifest). Clé = libellé de la séquence.
ALIASES: dict[str, tuple[str, ...]] = {
    "Dogme fragmenté": ("Doctrine ébranlée",),
    "Chute de Cropta": ("Fin de Crota", "Chute de Crota"),
}

# Semaine de référence observée : (début de semaine, slots par séquence).
REFERENCE_WEEK = datetime(2026, 10, 20, 17, 0, tzinfo=timezone.utc)
REFERENCE_SLOTS: dict[tuple[str, ...], tuple[str, ...]] = {
    RAID_SEQUENCE: ("Chute du Roi", "Jardin du Salut"),
    DUNGEON_SEQUENCE: ("Dogme fragmenté", "Étreinte de l'Avarice"),
}


# ── Normalisation des noms ─────────────────────────────────────────────


def norm_name(name: str) -> str:
    """Normalise un nom d'activité pour un matching tolérant.

    - ligature œ/Œ → 'oe' (NFKD ne la décompose pas)
    - minuscules, retrait de l'article initial (le/la/les/l')
    - suppression des accents (NFKD + filtrage des diacritiques)

    Vit dans la couche données (et non dans render/) parce que le matching
    séquence ↔ API en dépend : la résolution d'emote n'en est qu'un second
    consommateur.
    """
    s = name.replace("œ", "oe").replace("Œ", "OE")
    s = s.strip().lower()
    for art in ("le ", "la ", "les ", "l'"):
        if s.startswith(art):
            s = s[len(art):]
            break
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip()


def _labels(label: str) -> list[str]:
    """Formes normalisées d'une entrée de séquence (libellé + alias)."""
    return [norm_name(n) for n in (label, *ALIASES.get(label, ()))]


def find_index(name: str, sequence: tuple[str, ...]) -> int | None:
    """Position d'un nom d'activité dans la séquence, ou None.

    Deux passes : égalité stricte des formes normalisées (libellé ou alias),
    puis inclusion (le manifest Bungie est parfois plus verbeux que le libellé
    communautaire — « La Crypte de la Pierre Noire » vs « Crypte de la Pierre »)."""
    target = norm_name(name)
    if not target:
        return None

    for i, label in enumerate(sequence):
        if target in _labels(label):
            return i

    for i, label in enumerate(sequence):
        for label_n in _labels(label):
            if label_n and (label_n in target or target in label_n):
                return i

    return None


# ── Calendrier ─────────────────────────────────────────────────────────


def cycle_week_starts(count: int, now: datetime | None = None) -> list[int]:
    """Timestamps unix des `count` resets du mardi à partir de la semaine EN COURS."""
    first = last_weekday_reset(TUESDAY, now)
    return [int((first + timedelta(days=7 * i)).timestamp()) for i in range(count)]


def _weeks_since_reference(now: datetime | None = None) -> int:
    return (last_weekday_reset(TUESDAY, now) - REFERENCE_WEEK).days // 7


def reference_slots(
    sequence: tuple[str, ...], now: datetime | None = None
) -> list[int]:
    """Indices des slots de la semaine en cours d'après la semaine de référence."""
    ref = REFERENCE_SLOTS.get(sequence, ())
    weeks = _weeks_since_reference(now)
    out = []
    for name in ref:
        idx = find_index(name, sequence)
        if idx is not None:
            out.append((idx + weeks) % len(sequence))
    return out


# ── Prédiction ─────────────────────────────────────────────────────────


@dataclass
class RotationPrediction:
    """Cycle prédit : une entrée (timestamp_unix_du_reset, noms_des_slots) par
    semaine, la première étant la semaine EN COURS."""
    weeks: list[tuple[int, tuple[str, ...]]]
    # Activités featured de la semaine absentes de la séquence (hors cycle).
    unknown: list[str] = field(default_factory=list)
    # "api" (toutes les ancres viennent de l'API), "api+reference" (slot
    # complété), "reference" (aucune ancre API exploitable).
    source: str = "api"
    # True si on n'a pas pu reconstituer tous les slots attendus.
    partial: bool = False

    @property
    def slot_count(self) -> int:
        return len(self.weeks[0][1]) if self.weeks else 0


def predict_rotation(
    featured_names: list[str],
    sequence: tuple[str, ...],
    now: datetime | None = None,
) -> RotationPrediction | None:
    """Déroule un cycle complet à partir des activités featured de la semaine.

    Renvoie None seulement si rien ne permet d'ancrer (ni l'API, ni la
    référence)."""
    anchors: list[int] = []
    unknown: list[str] = []
    for name in featured_names:
        idx = find_index(name, sequence)
        if idx is None:
            unknown.append(name)
        elif idx not in anchors:
            anchors.append(idx)

    ref = reference_slots(sequence, now)
    expected = len(ref) or len(anchors)
    source = "api"

    if not anchors:
        if not ref:
            return None
        anchors, source = list(ref), "reference"
    elif len(anchors) < expected:
        # Complétion uniquement si l'API confirme la référence sur au moins un
        # slot : sinon la référence a dérivé et compléter induirait en erreur.
        if any(a in ref for a in anchors):
            for idx in ref:
                if idx not in anchors and len(anchors) < expected:
                    anchors.append(idx)
            source = "api+reference"

    # Ordre stable des slots (celui de la référence quand elle est cohérente).
    if ref and set(anchors) <= set(ref):
        anchors.sort(key=ref.index)

    size = len(sequence)
    starts = cycle_week_starts(size, now)
    weeks = [
        (ts, tuple(sequence[(idx + week) % size] for idx in anchors))
        for week, ts in enumerate(starts)
    ]
    return RotationPrediction(
        weeks=weeks,
        unknown=unknown,
        source=source,
        partial=len(anchors) < expected,
    )


def matches_reference(
    featured_names: list[str], sequence: tuple[str, ...], now: datetime | None = None
) -> bool | None:
    """True/False si les ancres API concordent avec la référence, None si on
    ne peut pas comparer. Sert au diagnostic (log) : un False durable signifie
    que Bungie a décalé la séquence et que REFERENCE_* est à mettre à jour."""
    ref = set(reference_slots(sequence, now))
    anchors = {i for i in (find_index(n, sequence) for n in featured_names) if i is not None}
    if not ref or not anchors:
        return None
    return anchors <= ref
