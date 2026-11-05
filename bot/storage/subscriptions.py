# -*- coding: utf-8 -*-
"""Abonnements centralisés (tous topics confondus), table bot_subscription.

En mémoire, organisés par serveur Discord :

{
  "<guild_id>": {
    "name": "Nom du serveur",                  # debug uniquement
    "topics": {
      "<topic>": {
        "<channel_or_thread_id>": {
          "name": "nom-du-salon",              # debug uniquement
          "is_thread": false,
          "role": "<role_id>" | null
        }
      }
    }
  }
}

Les champs `name` ne servent qu'à la lecture humaine de la base (debug) ;
toute la logique s'appuie uniquement sur les IDs.

Chargés une fois au démarrage (seul CE bot écrit ses lignes) : une
modification faite à la main dans la base n'est vue qu'au redémarrage.

Modèle /botconfig : un seul salon par topic + un seul rôle par topic. Le
schéma autorise techniquement plusieurs salons (ancien /alerte), mais
set_topic_destination réécrit toujours une entrée unique.
"""
from typing import Optional

from bot.core.config import BOT_ID
from bot.db.database import Database
from bot.storage.base import Table, flush
from bot.topics import TOPICS


class SubscriptionTable(Table):
    def __init__(self):
        super().__init__()
        self.data: dict = {}

    def touch(self, guild_id: str) -> None:
        self._touch(guild_id)

    def replace_all(self, data: dict) -> None:
        """Remplace tout (import des anciens fichiers JSON)."""
        for guild_id in set(self.data) | set(data):
            self._touch(guild_id)
        self.data = data

    async def _load(self, db: Database) -> None:
        self.data = {}
        for row in await db.fetchall(
            "SELECT guild_id, topic, channel_id, is_thread, role_id, guild_name, channel_name"
            " FROM bot_subscription WHERE bot_id = %s ORDER BY guild_id, topic",
            (BOT_ID,),
        ):
            guild = self.data.setdefault(str(row["guild_id"]), {"name": row["guild_name"], "topics": {}})
            guild["topics"].setdefault(row["topic"], {})[str(row["channel_id"])] = {
                "name": row["channel_name"],
                "is_thread": bool(row["is_thread"]),
                "role": str(row["role_id"]) if row["role_id"] else None,
            }

    async def _write(self, db: Database, keys: set) -> None:
        async with db.transaction() as cur:
            for guild_id in keys:
                await cur.execute(
                    "DELETE FROM bot_subscription WHERE bot_id = %s AND guild_id = %s",
                    (BOT_ID, int(guild_id)),
                )
                guild = self.data.get(guild_id)
                if not guild:
                    continue
                rows = [
                    (
                        BOT_ID, int(guild_id), topic, int(dest_id), int(bool(info.get("is_thread"))),
                        int(info["role"]) if info.get("role") else None,
                        guild.get("name"), info.get("name"),
                    )
                    for topic, dests in guild.get("topics", {}).items()
                    for dest_id, info in dests.items()
                ]
                if rows:
                    await cur.executemany(
                        "INSERT INTO bot_subscription (bot_id, guild_id, topic, channel_id,"
                        " is_thread, role_id, guild_name, channel_name)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        rows,
                    )


subscriptions = SubscriptionTable()


# ──────────────────────────────────────────────────────────────────────
# API publisher.
# ──────────────────────────────────────────────────────────────────────
def iter_subscribers(topic: str):
    """Itère les abonnés d'un topic : (guild_id, dest_id, info).
    `info` = {name, is_thread, role}."""
    for guild_id, guild in list(subscriptions.data.items()):
        for dest_id, info in list(guild.get("topics", {}).get(topic, {}).items()):
            yield guild_id, dest_id, dict(info)


# ──────────────────────────────────────────────────────────────────────
# API "single-channel" utilisée par /botconfig.
# ──────────────────────────────────────────────────────────────────────
def get_topic_destination(topic: str, guild_id: str) -> Optional[dict]:
    """Renvoie l'unique destination d'un topic pour ce serveur, ou None.

    Si d'anciennes données contiennent plusieurs salons (ancien /alerte),
    on retourne le premier — la prochaine validation /botconfig collapse
    automatiquement vers un seul salon.
    """
    guild = subscriptions.data.get(guild_id, {})
    dests = guild.get("topics", {}).get(topic, {})
    if not dests:
        return None
    channel_id, info = next(iter(dests.items()))
    return {
        "channel_id": channel_id,
        "is_thread": info.get("is_thread", False),
        "role": info.get("role"),
    }


async def set_topic_destination(
    topic: str,
    guild_id: str,
    channel_id: Optional[str],
    *,
    is_thread: bool = False,
    role_id: Optional[str] = None,
    guild_name: Optional[str] = None,
    channel_name: Optional[str] = None,
) -> None:
    """Écrit l'unique destination d'un topic (remplace tout l'existant).

    channel_id=None → désactive le topic pour ce serveur (nettoyage des
    dicts vides).
    """
    data = subscriptions.data
    subscriptions.touch(guild_id)

    if channel_id is None:
        guild = data.get(guild_id)
        if guild:
            topics = guild.get("topics", {})
            topics.pop(topic, None)
            if not topics:
                data.pop(guild_id, None)
        await flush()
        return

    guild = data.setdefault(guild_id, {"name": guild_name, "topics": {}})
    if guild_name:
        guild["name"] = guild_name
    guild.setdefault("topics", {})
    guild["topics"][topic] = {
        str(channel_id): {
            "name": channel_name,
            "is_thread": is_thread,
            "role": role_id,
        }
    }
    await flush()


def load_config_state(guild_id) -> dict:
    """État complet (tous topics) pour l'UI /botconfig.

    Forme : { topic: {"channel_id": str|None, "is_thread": bool, "role_id": str|None} }
    """
    gid = str(guild_id)
    state: dict[str, dict] = {}
    for topic in TOPICS:
        dest = get_topic_destination(topic, gid)
        if dest:
            state[topic] = {
                "channel_id": dest["channel_id"],
                "is_thread": dest["is_thread"],
                "role_id": dest["role"],
            }
        else:
            state[topic] = {"channel_id": None, "is_thread": False, "role_id": None}
    return state
