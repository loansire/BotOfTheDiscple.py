# -*- coding: utf-8 -*-
"""État du calcul (table compute_state) : petites valeurs nommées en JSON.

Clés utilisées :
- pipeline.last_reset / pipeline.pending_weekdays (bot/storage/pipeline_state.py)
- weekly.signature.<topic>, weekly.vanguard_challenges (bot/features/weekly/state.py)
- news.last_id.<mot-clé> (bot/features/news/state.py)
- maintenance.<jeu> (bot/features/maintenance/state.py)
- bungie.oauth (bot/bungie/oauth.py)

Les valeurs renvoyées par get() sont PARTAGÉES avec le cache : l'appelant qui
veut les modifier doit passer par set()."""
from __future__ import annotations

import json

from bot.db.database import Database
from bot.storage.base import Table, flush

_MISSING = object()


class ComputeState(Table):
    def __init__(self):
        super().__init__()
        self._values: dict[str, object] = {}

    def get(self, name: str, default=None):
        return self._values.get(name, default)

    def set(self, name: str, value) -> None:
        self._values[name] = value
        self._touch(name)

    def delete(self, name: str) -> None:
        if self._values.pop(name, _MISSING) is not _MISSING:
            self._touch(name)

    async def save(self) -> None:
        await flush()

    async def _load(self, db: Database) -> None:
        self._values = {
            row["name"]: json.loads(row["value"])
            for row in await db.fetchall("SELECT name, value FROM compute_state")
        }

    async def _write(self, db: Database, keys: set) -> None:
        async with db.transaction() as cur:
            for name in keys:
                if name not in self._values:
                    await cur.execute("DELETE FROM compute_state WHERE name = %s", (name,))
                    continue
                await cur.execute(
                    "INSERT INTO compute_state (name, value) VALUES (%s, %s)"
                    " ON DUPLICATE KEY UPDATE value = VALUES(value)",
                    (name, json.dumps(self._values[name], ensure_ascii=False)),
                )


compute_state = ComputeState()
