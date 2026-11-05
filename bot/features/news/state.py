# -*- coding: utf-8 -*-
"""État persistant anti-doublon des articles déjà annoncés (par mot-clé).
compute_state, clés `news.last_id.<mot-clé>`."""
from bot.storage.compute_state import compute_state


class NewsState:
    def last_id(self, keyword: str) -> str:
        return compute_state.get(f"news.last_id.{keyword}", "")

    def set_last_id(self, keyword: str, article_id: str):
        compute_state.set(f"news.last_id.{keyword}", article_id)

    async def save(self) -> None:
        await compute_state.save()
