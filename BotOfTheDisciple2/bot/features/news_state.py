# -*- coding: utf-8 -*-
"""État persistant anti-doublon des articles déjà annoncés (par mot-clé)."""
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "news_state.json"


class NewsState:
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

    def last_id(self, keyword: str) -> str:
        return self._data.get(keyword, "")

    def set_last_id(self, keyword: str, article_id: str):
        self._data[keyword] = article_id