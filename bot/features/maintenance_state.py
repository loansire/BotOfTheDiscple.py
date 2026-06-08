# -*- coding: utf-8 -*-
"""État persistant anti-spam, par jeu."""
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "state.json"


class MaintenanceState:
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

    def get(self, game: str) -> dict:
        return self._data.get(game, {})

    def set(self, game: str, state: dict):
        self._data[game] = state