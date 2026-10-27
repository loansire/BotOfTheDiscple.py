# -*- coding: utf-8 -*-
"""État persistant anti-doublon des articles déjà annoncés (par mot-clé)."""
from bot.config import ALERTS_DIR
from bot.utils.json_store import JsonStore

STATE_PATH = ALERTS_DIR / "news_state.json"


class NewsState(JsonStore):
    def __init__(self, path=STATE_PATH):
        super().__init__(path)

    def last_id(self, keyword: str) -> str:
        return self._data.get(keyword, "")

    def set_last_id(self, keyword: str, article_id: str):
        self._data[keyword] = article_id