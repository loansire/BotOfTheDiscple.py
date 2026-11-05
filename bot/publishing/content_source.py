# -*- coding: utf-8 -*-
"""Côté publication : lecture d'une publication prête en base.

Un Snapshot fige UNE version d'un topic (messages + images) : tous les
serveurs d'un même passage reçoivent exactement le même contenu, et le hash
enregistré par le calcul sert d'identité (serveur déjà à jour = même hash)."""
from __future__ import annotations

from dataclasses import dataclass

from bot.content import store
from bot.content.model import DEFAULT_VARIANT, Message, Post
from bot.render.components import Rendered, image_ids, render


@dataclass
class Snapshot:
    post: Post
    messages: list[Message]
    images: dict[str, bytes]

    @property
    def hash(self) -> str:
        return self.post.stored_hash or ""

    def render(self, index: int = 0) -> Rendered:
        """Rendu du message `index` (objets Discord et fichiers NEUFS)."""
        return render(self.messages[index], self.images)

    def render_all(self) -> list[Rendered]:
        return [render(m, self.images) for m in self.messages]


async def snapshot(topic: str, variant: str = DEFAULT_VARIANT) -> Snapshot | None:
    """Dernière version prête du topic, ou None si rien n'a encore été calculé."""
    post = await store.load_post(topic)
    if post is None:
        return None
    messages = post.variants.get(variant, [])
    if not messages:
        return None
    ids = set().union(*(image_ids(m) for m in messages))
    return Snapshot(post, messages, await store.load_images(ids))
