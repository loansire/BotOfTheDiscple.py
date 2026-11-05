# -*- coding: utf-8 -*-
"""Messages publiés par CE bot (tables bot_message + bot_publication).

Une entrée par (serveur, topic) : les IDs de messages rangés par `slot`
('content' = messages de contenu + ping, 'status' = statut Xûr) et le hash du
contenu publié (vide = à republier).

Les états exposés aux moteurs de publication sont des vues PAR TOPIC sur
cette table unique :
- MultiMessageState  : N messages jetables par serveur + hash
  (Ada-1, Eververse, secteurs oubliés, Avant-garde) ;
- SingleMessageState : 1 message par serveur + hash
  (raids, donjons, défis ascendants, distorsion).
L'état Xûr (statut + catégories) est dans bot/features/xur/state.py."""
from __future__ import annotations

from dataclasses import dataclass, field

from bot.core.config import BOT_ID
from bot.db.database import Database
from bot.storage.base import Table, flush

CONTENT = "content"


@dataclass
class Entry:
    slots: dict[str, list[str]] = field(default_factory=dict)
    hash: str | None = None


class MessageTable(Table):
    def __init__(self):
        super().__init__()
        self._entries: dict[tuple[str, str], Entry] = {}

    # ── Lecture ───────────────────────────────────────────────────────
    def get(self, guild_id, topic: str) -> Entry | None:
        return self._entries.get((str(guild_id), topic))

    def guilds(self, topic: str) -> list[str]:
        return [gid for (gid, t) in self._entries if t == topic]

    # ── Écriture ──────────────────────────────────────────────────────
    def put(self, guild_id, topic: str, entry: Entry) -> None:
        key = (str(guild_id), topic)
        self._entries[key] = entry
        self._touch(key)

    def drop(self, guild_id, topic: str) -> None:
        key = (str(guild_id), topic)
        self._entries.pop(key, None)
        self._touch(key)

    # ── Persistance ───────────────────────────────────────────────────
    async def _load(self, db: Database) -> None:
        self._entries = {}
        for row in await db.fetchall(
            "SELECT guild_id, topic, content_hash FROM bot_publication WHERE bot_id = %s", (BOT_ID,)
        ):
            self._entries[(str(row["guild_id"]), row["topic"])] = Entry(hash=row["content_hash"])
        for row in await db.fetchall(
            "SELECT guild_id, topic, slot, message_id FROM bot_message"
            " WHERE bot_id = %s ORDER BY guild_id, topic, slot, position",
            (BOT_ID,),
        ):
            entry = self._entries.setdefault((str(row["guild_id"]), row["topic"]), Entry())
            entry.slots.setdefault(row["slot"], []).append(str(row["message_id"]))

    async def _write(self, db: Database, keys: set) -> None:
        async with db.transaction() as cur:
            for guild_id, topic in keys:
                where = (BOT_ID, int(guild_id), topic)
                await cur.execute(
                    "DELETE FROM bot_message WHERE bot_id = %s AND guild_id = %s AND topic = %s", where
                )
                entry = self._entries.get((guild_id, topic))
                if entry is None:
                    await cur.execute(
                        "DELETE FROM bot_publication WHERE bot_id = %s AND guild_id = %s AND topic = %s",
                        where,
                    )
                    continue
                await cur.execute(
                    "INSERT INTO bot_publication (bot_id, guild_id, topic, content_hash)"
                    " VALUES (%s, %s, %s, %s)"
                    " ON DUPLICATE KEY UPDATE content_hash = VALUES(content_hash)",
                    (*where, entry.hash),
                )
                rows = [
                    (*where, slot, pos, int(mid))
                    for slot, ids in entry.slots.items()
                    for pos, mid in enumerate(ids)
                ]
                if rows:
                    await cur.executemany(
                        "INSERT INTO bot_message (bot_id, guild_id, topic, slot, position, message_id)"
                        " VALUES (%s, %s, %s, %s, %s, %s)",
                        rows,
                    )


messages = MessageTable()


class _TopicState:
    """Vue d'un topic de la table des messages."""

    def __init__(self, topic: str):
        self.topic = topic

    def _entry(self, guild_id) -> Entry | None:
        return messages.get(guild_id, self.topic)

    def purge(self, guild_id) -> None:
        """Oublie tout l'état d'un serveur (retrait du salon)."""
        messages.drop(guild_id, self.topic)

    async def save(self) -> None:
        await flush()


class MultiMessageState(_TopicState):
    """N messages JETABLES par serveur : supprimés puis republiés à chaque
    changement de contenu (repost → notification + ping rôle)."""

    def get(self, guild_id) -> dict:
        """Entrée normalisée : {message_ids: [...], hash: str}."""
        entry = self._entry(guild_id)
        if entry is None:
            return {"message_ids": [], "hash": ""}
        return {"message_ids": list(entry.slots.get(CONTENT, [])), "hash": entry.hash or ""}

    def message_ids(self, guild_id) -> list:
        return self.get(guild_id)["message_ids"]

    def content_hash(self, guild_id) -> str:
        return self.get(guild_id)["hash"]

    def iter_guilds(self):
        """Itère (guild_id, entry_normalisée) pour tous les serveurs connus."""
        for guild_id in messages.guilds(self.topic):
            yield guild_id, self.get(guild_id)

    def set(self, guild_id, *, message_ids=None, content_hash=None) -> None:
        """Met à jour sélectivement les champs fournis (les autres conservés)."""
        current = self.get(guild_id)
        ids = list(message_ids) if message_ids is not None else current["message_ids"]
        new_hash = content_hash if content_hash is not None else current["hash"]
        messages.put(guild_id, self.topic, Entry(slots={CONTENT: [str(i) for i in ids]}, hash=new_hash))

    async def invalidate(self) -> None:
        """Efface les hashes pour forcer un repost au prochain publish.

        Les IDs sont CONSERVÉS : le moteur en a besoin pour supprimer les
        anciens messages avant repost. Utilisé par /refresh."""
        for guild_id in messages.guilds(self.topic):
            self.set(guild_id, content_hash="")
        await self.save()


class SingleMessageState(_TopicState):
    """UN message par serveur + un `hash` identifiant le contenu affiché."""

    def get(self, guild_id) -> dict:
        """Entrée d'un serveur ({message_id, hash}), valeurs None si absent."""
        entry = self._entry(guild_id)
        if entry is None:
            return {"message_id": None, "hash": None}
        ids = entry.slots.get(CONTENT, [])
        return {"message_id": ids[0] if ids else None, "hash": entry.hash}

    def iter_guilds(self):
        for guild_id in messages.guilds(self.topic):
            yield guild_id, self.get(guild_id)

    def set(self, guild_id, *, message_id, content_hash) -> None:
        messages.put(
            guild_id, self.topic, Entry(slots={CONTENT: [str(message_id)]}, hash=content_hash)
        )

    async def invalidate(self) -> None:
        """Efface les hash (conserve les message_id) → force une ré-édition au
        prochain publish."""
        for guild_id in messages.guilds(self.topic):
            entry = messages.get(guild_id, self.topic)
            messages.put(guild_id, self.topic, Entry(slots=entry.slots, hash=None))
        await self.save()
