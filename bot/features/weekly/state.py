# -*- coding: utf-8 -*-
"""État des messages persistants weekly/daily + mémoire de la période.

Messages (bot/storage/messages.py), un état par topic :
- multi-message (secteurs oubliés, Avant-garde) : weekly_slot(topic) ;
- mono-message (raids, donjons) : weekly_single(topic).

Mémoire du calcul (compute_state), via weekly_state() :
- signatures de contenu par topic (garde-fou données périmées, cf.
  freshness.py) : clés `weekly.signature.<topic>` ;
- défis Avant-garde vus pendant la semaine : clé `weekly.vanguard_challenges`.

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique
source de vérité (PipelineState).

Le `hash` évite de reposter un message dont le contenu n'a pas changé. Le
refresh manuel passe par `invalidate()`. Le retrait d'un salon via /botconfig
passe par `purge()`.
"""
from functools import cache

from bot.storage.compute_state import compute_state
from bot.storage.messages import MultiMessageState, SingleMessageState

_SIGNATURE = "weekly.signature."
_CHALLENGES = "weekly.vanguard_challenges"


class WeeklyMemory:
    # ── Signatures de contenu (garde-fou données périmées) ────────────
    def last_signature(self, topic: str) -> dict:
        """Dernier contenu publié pour un topic, tous serveurs confondus :
        {"period": "<iso début de période>", "sig": [...]} (vide si inconnu)."""
        return compute_state.get(_SIGNATURE + topic, {})

    def set_signature(self, topic: str, period_iso: str, sig: list[str]):
        compute_state.set(_SIGNATURE + topic, {"period": period_iso, "sig": sorted(sig)})

    # ── Défis de la semaine (Avant-garde) ─────────────────────────────
    def week_challenges(self, week_iso: str) -> dict[int, int]:
        """Défis Avant-garde vus pendant la semaine `week_iso` (début = reset
        du mardi) : {activity_hash: arme défi}. Vide pour une autre semaine."""
        saved = compute_state.get(_CHALLENGES, {})
        if saved.get("week") != week_iso:
            return {}
        return {int(k): int(v) for k, v in saved.get("items", {}).items()}

    def set_week_challenges(self, week_iso: str, items: dict[int, int]):
        compute_state.set(
            _CHALLENGES, {"week": week_iso, "items": {str(k): v for k, v in items.items()}}
        )

    async def save(self) -> None:
        await compute_state.save()


@cache
def weekly_state() -> WeeklyMemory:
    """Instance UNIQUE partagée."""
    return WeeklyMemory()


@cache
def weekly_slot(topic: str) -> MultiMessageState:
    """État d'un topic multi-message (secteurs, Avant-garde)."""
    return MultiMessageState(topic)


@cache
def weekly_single(topic: str) -> SingleMessageState:
    """État d'un topic mono-message (raids, donjons)."""
    return SingleMessageState(topic)
