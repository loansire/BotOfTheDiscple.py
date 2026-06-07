# -*- coding: utf-8 -*-
"""Store d'abonnements centralisé (tous topics confondus).

Un unique fichier `subscriptions.json`, organisé par serveur Discord :

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

NB : cette couche isole le stockage. Migrer vers SQL ne touchera QUE ce module
(is_subscribed / subscribe / unsubscribe / iter_subscribers).
"""
import json
from typing import Optional

from bot.config import ALERTS_DIR

STORE_PATH = ALERTS_DIR / "subscriptions.json"


def _load_all() -> dict:
    if STORE_PATH.exists():
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_all(data: dict) -> None:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_subscribed(topic: str, guild_id: str, dest_id: str) -> bool:
    """True si ce salon/thread est déjà abonné à ce topic."""
    guild = _load_all().get(guild_id, {})
    return dest_id in guild.get("topics", {}).get(topic, {})


def subscribe(
    topic: str,
    guild_id: str,
    dest_id: str,
    *,
    is_thread: bool,
    guild_name: Optional[str] = None,
    channel_name: Optional[str] = None,
    role_id: Optional[str] = None,
) -> None:
    """Abonne (ou met à jour) un salon/thread à un topic.
    `guild_name` / `channel_name` ne servent qu'au debug et sont rafraîchis
    à chaque appel."""
    data = _load_all()

    guild = data.setdefault(guild_id, {"name": guild_name, "topics": {}})
    if guild_name:
        guild["name"] = guild_name
    guild.setdefault("topics", {})

    topic_dests = guild["topics"].setdefault(topic, {})
    topic_dests[dest_id] = {
        "name": channel_name,
        "is_thread": is_thread,
        "role": role_id,
    }
    _save_all(data)


def unsubscribe(topic: str, guild_id: str, dest_id: str) -> bool:
    """Désabonne un salon/thread. True si un abonnement a été retiré.
    Nettoie les dicts devenus vides (topic puis guild)."""
    data = _load_all()
    guild = data.get(guild_id)
    if not guild:
        return False

    topics = guild.get("topics", {})
    dests = topics.get(topic, {})
    removed = dests.pop(dest_id, None) is not None

    if not dests:
        topics.pop(topic, None)
    if not topics:
        data.pop(guild_id, None)

    _save_all(data)
    return removed


def iter_subscribers(topic: str):
    """Itère les abonnés d'un topic : (guild_id, dest_id, info).
    `info` = {name, is_thread, role}."""
    for guild_id, guild in _load_all().items():
        for dest_id, info in guild.get("topics", {}).get(topic, {}).items():
            yield guild_id, dest_id, info