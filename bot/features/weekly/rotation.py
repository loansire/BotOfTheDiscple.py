# -*- coding: utf-8 -*-
"""Rotation prédictive des raids & donjons hebdomadaires.

Logique PURE : aucun appel réseau, aucune dépendance Discord. À partir des
activités *featured* de la semaine (celles déjà publiées par la feature weekly,
issues de l'API), on retrouve la position de chaque slot dans la séquence
canonique, puis on déroule un cycle complet.

Pourquoi PAS de date d'ancrage codée en dur : la séquence est stable, mais son
point d'entrée peut être décalé par Bungie (extension, hotfix, semaine
exceptionnelle). En ré-ancrant à CHAQUE appel sur les données API de la semaine
en cours, la prédiction se recale d'elle-même et ne peut pas dériver.

Si un nom featured n'existe pas dans la séquence (nouveau raid ajouté au pool,
renommage manifest), `predict_rotation` renvoie None : l'appelant affiche un
repli explicite plutôt qu'une prédiction fausse.

Les libellés des séquences sont exactement ceux des tables d'emotes (cf.
bot/embeds/activity_emojis.py) : l'emote est donc toujours résolue, et un seul
endroit à éditer quand une activité entre dans la rotation.
"""
from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta

from bot.bungie.reset import TUESDAY, next_weekday_reset

# ── Séquences canoniques ───────────────────────────────────────────────
# Les DEUX slots (raid A / raid B) parcourent la MÊME séquence avec des
# décalages différents. Un cycle complet dure donc len(sequence) semaines.
# Les activités PERMANENTES (Désert Perpétuel, Équilibre) n'en font pas
# partie et sont exclues en amont par l'appelant.

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


# ── Normalisation des noms ─────────────────────────────────────────────


def norm_name(name: str) -> str:
    """Normalise un nom d'activité pour un matching tolérant.

    - ligature œ/Œ → 'oe' (NFKD ne la décompose pas)
    - minuscules, retrait de l'article initial (le/la/les/l')
    - suppression des accents (NFKD + filtrage des diacritiques)

    Vit dans la couche données (et non dans embeds/) parce que le matching
    séquence ↔ API en dépend : la résolution d'emote n'en est qu'un second
    consommateur.
    """
    s = name.replace("œ", "oe").replace("Œ", "OE").replace("\u0153", "oe")
    s = s.strip().lower()
    for art in ("le ", "la ", "les ", "l'"):
        if s.startswith(art):
            s = s[len(art):]
            break
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip()


def find_index(name: str, sequence: tuple[str, ...]) -> int | None:
    """Position d'un nom d'activité dans la séquence, ou None.

    Deux passes : égalité stricte des formes normalisées, puis inclusion
    (le manifest Bungie est parfois plus verbeux que le libellé communautaire —
    « La Crypte de la Pierre Noire » vs « Crypte de la Pierre »)."""
    target = norm_name(name)
    if not target:
        return None

    for i, label in enumerate(sequence):
        if norm_name(label) == target:
            return i

    for i, label in enumerate(sequence):
        label_n = norm_name(label)
        if label_n and (label_n in target or target in label_n):
            return i

    return None


# ── Calendrier ─────────────────────────────────────────────────────────


def cycle_week_starts(count: int, now: datetime | None = None) -> list[int]:
    """Timestamps unix des `count` resets du mardi à partir de la semaine EN COURS.

    La semaine en cours a commencé au reset du mardi précédent, soit le
    prochain reset du mardi moins 7 jours (next_weekday_reset gère déjà le cas
    « on est mardi mais avant l'heure du reset »)."""
    first = next_weekday_reset(TUESDAY, now) - timedelta(days=7)
    return [int((first + timedelta(days=7 * i)).timestamp()) for i in range(count)]


# ── Prédiction ─────────────────────────────────────────────────────────


def predict_rotation(
    featured_names: list[str],
    sequence: tuple[str, ...],
    now: datetime | None = None,
) -> list[tuple[int, tuple[str, ...]]] | None:
    """Déroule un cycle complet à partir des activités featured de la semaine.

    Renvoie une liste de (timestamp_unix_du_reset, noms_des_slots), longue de
    len(sequence) semaines — la première entrée étant la semaine EN COURS.
    Renvoie None si l'ancrage est impossible (liste vide, ou nom inconnu de la
    séquence) : mieux vaut ne rien prédire qu'induire en erreur.
    """
    anchors: list[int] = []
    for name in featured_names:
        idx = find_index(name, sequence)
        if idx is None:
            return None  # ancrage incertain → pas de prédiction
        if idx not in anchors:
            anchors.append(idx)

    if not anchors:
        return None

    size = len(sequence)
    starts = cycle_week_starts(size, now)
    return [
        (ts, tuple(sequence[(idx + week) % size] for idx in anchors))
        for week, ts in enumerate(starts)
    ]