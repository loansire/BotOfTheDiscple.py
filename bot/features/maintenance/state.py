# -*- coding: utf-8 -*-
"""État persistant anti-spam, par jeu."""
from bot.core.config import ALERTS_DIR
from bot.storage.json_store import JsonStore

STATE_PATH = ALERTS_DIR / "state.json"


class MaintenanceState(JsonStore):
    def __init__(self, path=STATE_PATH):
        super().__init__(path)

    def get(self, game: str) -> dict:
        return self._data.get(game, {})

    def set(self, game: str, state: dict):
        self._data[game] = state