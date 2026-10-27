# -*- coding: utf-8 -*-
"""État de la pipeline de reset : unique source de vérité du dernier reset traité.

Un seul scalaire global `last_reset_iso` — le reset Bungie est global (17:00
UTC), pas par serveur Discord. Les états de messages PAR serveur restent dans
WeeklyMessageState / XurMessageState.

Fichier :
{
  "last_reset": "<iso>"   # dernier reset quotidien déjà traité par la pipeline
}
"""
from bot.core.config import ALERTS_DIR
from bot.storage.json_store import JsonStore

STATE_PATH = ALERTS_DIR / "pipeline_state.json"


class PipelineState(JsonStore):
    def __init__(self, path=STATE_PATH):
        super().__init__(path)

    @property
    def last_reset_iso(self) -> str:
        return self._data.get("last_reset", "")

    @last_reset_iso.setter
    def last_reset_iso(self, value: str):
        self._data["last_reset"] = value
    @property
    def pending_weekdays(self) -> list[int]:
        """Jours de semaine des resets détectés mais pas encore traités avec
        succès (hold mode). Persisté : si une maintenance du mardi déborde sur
        le reset du mercredi, les étapes du mardi restent dues."""
        return list(self._data.get("pending_weekdays", []))

    @pending_weekdays.setter
    def pending_weekdays(self, value: list[int]):
        if value:
            self._data["pending_weekdays"] = sorted(set(value))
        else:
            self._data.pop("pending_weekdays", None)
