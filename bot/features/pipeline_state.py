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
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "pipeline_state.json"


class PipelineState:
    def __init__(self, path=STATE_PATH):
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @property
    def last_reset_iso(self) -> str:
        return self._data.get("last_reset", "")

    @last_reset_iso.setter
    def last_reset_iso(self, value: str):
        self._data["last_reset"] = value