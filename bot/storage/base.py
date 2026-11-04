# -*- coding: utf-8 -*-
"""Socle commun des stores SQL : cache mémoire + écriture différée explicite.

Chaque table (abonnements, messages, état du calcul...) est chargée ENTIÈREMENT
en mémoire au démarrage : les lectures restent synchrones et instantanées
(elles sont appelées plusieurs fois par minute par les boucles). Les
modifications marquent des clés « sales » ; `await flush()` (appelé par les
`save()` des états) écrit toutes les clés sales de toutes les tables.

Un échec d'écriture (base injoignable) remet les clés en « sales » et relève
l'exception : la pipeline passe alors en hold mode et retente plus tard, sans
rien perdre de ce qui est en mémoire.

Sans base ouverte (tests), `flush()` ne fait rien : les stores fonctionnent en
mémoire seule."""
from __future__ import annotations

import asyncio

from bot.db.database import Database, get_db

_TABLES: list["Table"] = []
_flush_lock = asyncio.Lock()


class Table:
    """Une table SQL mise en cache. Les sous-classes implémentent `_load` et
    `_write(db, keys)` ; elles appellent `_touch(key)` après chaque mutation."""

    def __init__(self):
        self._dirty: set = set()
        _TABLES.append(self)

    def _touch(self, key) -> None:
        self._dirty.add(key)

    async def _load(self, db: Database) -> None:
        raise NotImplementedError

    async def _write(self, db: Database, keys: set) -> None:
        raise NotImplementedError

    async def load(self, db: Database) -> None:
        await self._load(db)
        self._dirty.clear()


async def load_all() -> None:
    db = get_db()
    if db is None:
        return
    for table in _TABLES:
        await table.load(db)


async def flush() -> None:
    """Écrit en base toutes les modifications en attente (toutes tables)."""
    db = get_db()
    async with _flush_lock:
        for table in _TABLES:
            if not table._dirty:
                continue
            keys, table._dirty = table._dirty, set()
            if db is None:
                continue
            try:
                await table._write(db, keys)
            except BaseException:
                table._dirty |= keys
                raise
