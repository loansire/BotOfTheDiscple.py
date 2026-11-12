# -*- coding: utf-8 -*-
"""Étapes de CALCUL branchées sur les publications, par topic.

Les publications (bot/publishing/catalog.py) ne connaissent pas le calcul :
elles publient la dernière version rangée en base. Le bot qui calcule (live)
enregistre ici, au démarrage, la fonction qui produit chaque topic (cf.
bot/features/producers.py) ; une publication l'appelle alors juste avant de
lire la base. Un bot qui ne fait que publier (lite) n'enregistre rien.

Signatures (selon le moteur du topic) :
- repost / single : produce(strict: bool) -> bool  (False = rien à publier) ;
- edit_in_place   : produce(force: bool) -> None ;
- Xûr             : produce() -> bool (catégories), produce() -> None (statut)."""
from __future__ import annotations

from typing import Callable

_PRODUCERS: dict[str, Callable] = {}


def register(topic: str, produce: Callable) -> None:
    _PRODUCERS[topic] = produce


def get(topic: str) -> Callable | None:
    return _PRODUCERS.get(topic)


def clear() -> None:
    """Tests : oublie tous les calculs enregistrés."""
    _PRODUCERS.clear()
