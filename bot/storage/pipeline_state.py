# -*- coding: utf-8 -*-
"""État de la pipeline de reset : unique source de vérité du dernier reset traité.

Un seul scalaire global `last_reset_iso` — le reset Bungie est global (17:00
UTC), pas par serveur Discord. Les états de messages PAR serveur restent dans
bot/storage/messages.py.

Persisté dans compute_state (clés `pipeline.*`)."""
from functools import cache

from bot.storage.compute_state import compute_state

_LAST_RESET = "pipeline.last_reset"
_PENDING = "pipeline.pending_weekdays"


class PipelineState:
    @property
    def last_reset_iso(self) -> str:
        return compute_state.get(_LAST_RESET, "")

    @last_reset_iso.setter
    def last_reset_iso(self, value: str):
        compute_state.set(_LAST_RESET, value)

    @property
    def pending_weekdays(self) -> list[int]:
        """Jours de semaine des resets détectés mais pas encore traités avec
        succès (hold mode). Persisté : si une maintenance du mardi déborde sur
        le reset du mercredi, les étapes du mardi restent dues."""
        return list(compute_state.get(_PENDING, []))

    @pending_weekdays.setter
    def pending_weekdays(self, value: list[int]):
        if value:
            compute_state.set(_PENDING, sorted(set(value)))
        else:
            compute_state.delete(_PENDING)

    async def save(self) -> None:
        await compute_state.save()


@cache
def pipeline_state() -> PipelineState:
    """Instance UNIQUE partagée."""
    return PipelineState()
