# -*- coding: utf-8 -*-
"""Outils de test des stores SQL : remise à zéro des caches mémoire et fausse
base qui enregistre les requêtes."""
from __future__ import annotations

from contextlib import asynccontextmanager

from bot.storage import base
from bot.storage.compute_state import compute_state
from bot.storage.messages import messages
from bot.storage.subscriptions import subscriptions


def reset_memory() -> None:
    """Vide tous les caches (chaque test part d'une base vide)."""
    messages._entries = {}
    compute_state._values = {}
    subscriptions.data = {}
    for table in base._TABLES:
        table._dirty.clear()


class RecordingCursor:
    def __init__(self, log: list):
        self._log = log

    async def execute(self, sql, args=None):
        self._log.append((" ".join(sql.split()), args))

    async def executemany(self, sql, rows):
        for row in rows:
            self._log.append((" ".join(sql.split()), row))


class RecordingDatabase:
    """Fausse base : SELECT → lignes préparées par requête, écritures notées."""

    def __init__(self, rows: dict[str, list[dict]] | None = None, *, fail: bool = False):
        self.rows = rows or {}
        self.writes: list[tuple[str, object]] = []
        self.fail = fail

    async def fetchall(self, sql, args=None):
        for needle, rows in self.rows.items():
            if needle in sql:
                return rows
        return []

    async def execute(self, sql, args=None):
        self.writes.append((" ".join(sql.split()), args))
        return 1

    @asynccontextmanager
    async def transaction(self):
        if self.fail:
            raise ConnectionError("base injoignable")
        pending: list = []
        yield RecordingCursor(pending)
        self.writes.extend(pending)


class FakeContentStore:
    """Remplaçant en mémoire de bot.content.store (save / load / images)."""

    def __init__(self):
        self.posts: dict = {}
        self.images: dict[str, bytes] = {}

    async def save_post(self, post):
        latest = self.posts.get(post.topic)
        content_hash = post.content_hash()
        if latest is not None and latest.stored_hash == content_hash:
            post.version, post.stored_hash = latest.version, content_hash
            return latest.version, False
        post.version = (latest.version if latest else 0) + 1
        post.stored_hash = content_hash
        self.images.update({i: data for i, (data, _) in post.images().items()})
        self.posts[post.topic] = post
        return post.version, True

    async def load_post(self, topic, version=None):
        return self.posts.get(topic)

    async def load_images(self, image_ids):
        return {i: self.images[i] for i in image_ids if i in self.images}

    def patch(self):
        from unittest import mock

        return mock.patch.multiple(
            "bot.content.store",
            save_post=self.save_post,
            load_post=self.load_post,
            load_images=self.load_images,
        )
