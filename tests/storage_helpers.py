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
