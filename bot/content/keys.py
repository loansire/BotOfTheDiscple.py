# -*- coding: utf-8 -*-
"""Noms partagés entre le calcul (qui écrit le contenu) et la publication (qui
le lit et traite les clics) : topics, variantes et custom_id.

C'est le contrat entre les deux côtés : un bot qui ne fait que publier (lite)
s'appuie uniquement sur ce module, jamais sur bot/features."""
from __future__ import annotations

# ── Maintenances ────────────────────────────────────────────────────────
COPY = "copy"  # variante : texte prêt à copier


def maintenance_topic(game: str) -> str:
    return f"maintenance_{game}"


def maintenance_end_topic(game: str) -> str:
    return f"maintenance_{game}_end"


# ── News (bascule de langue) ────────────────────────────────────────────
EN, FR, CHECK = "en", "fr", "check"


def news_action(topic: str, what: str) -> str:
    return f"news:{topic}:{what}"


# ── Tables de butin (pagination) ────────────────────────────────────────


def loot_topic(key: str) -> str:
    return f"loot:{key}"


def loot_page_variant(page: int) -> str:
    """Variante d'une page (1 = première)."""
    return f"p{page}"


def loot_page_action(key: str, page: int) -> str:
    return f"loot:{key}:{page}"


# ── Wishwall ────────────────────────────────────────────────────────────
WISHWALL_TOPIC = "wishwall"
WISHWALL_SELECT_ID = "wishwall:select"


# ── Rotation prédictive (bouton des messages raids / donjons) ───────────


def rotation_topic(kind: str) -> str:
    """kind : 'raid' ou 'dungeon'."""
    return f"rotation_{kind}"


# ── Xûr ─────────────────────────────────────────────────────────────────
XUR_TOPIC = "xur"
XUR_STATUS_TOPIC = "xur_status"
XUR_PRESENT, XUR_ABSENT = "present", "absent"  # variantes du statut
