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

NB : cette couche isole le stockage. Migrer vers SQL ne touchera QUE ce module.

Modèle /botconfig : un seul salon par topic + un seul rôle par topic. Le
schéma autorise techniquement plusieurs salons (ancien /alerte), mais
set_topic_destination réécrit toujours une entrée unique.
"""
import json
from typing import Optional

from bot.config import ALERTS_DIR

STORE_PATH = ALERTS_DIR / "subscriptions.json"


# ──────────────────────────────────────────────────────────────────────
# Registre central des topics configurables (source unique de vérité).
# label/emoji utilisés par l'UI /botconfig.
# ──────────────────────────────────────────────────────────────────────
TOPICS: dict[str, dict] = {
    "maintenance_destiny": {
        "label": "Maintenance - Destiny 2",
        "emoji": "<:D2:1270042220627497020>",
    },
    "maintenance_marathon": {
        "label": "Maintenance - Marathon",
        "emoji": "<:Marathon:1513347065881559273>",
    },
    "news_patch_note": {
        "label": "Patch Note - Destiny 2",
        "emoji": "📝",
    },
    "news_twid": {
        "label": "This Week in Destiny",
        "emoji": "📰",
    },
    "weekly_raid_dungeon": {
        "label": "Raids & Donjons de la semaine",
        "emoji": "<:Raid:1338595321319788595>",
    },
    "daily_lost_sector": {
        "label": "Secteurs Oubliés du jour",
        "emoji": "<:Secteur:1270042203577778246>",
    },
}


def _load_all() -> dict:
    if STORE_PATH.exists():
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_all(data: dict) -> None:
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────
# API d'origine (publisher + compat).
# ──────────────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────────────
# API "single-channel" utilisée par /botconfig.
# ──────────────────────────────────────────────────────────────────────
def get_topic_destination(topic: str, guild_id: str) -> Optional[dict]:
    """Renvoie l'unique destination d'un topic pour ce serveur, ou None.

    Si d'anciennes données contiennent plusieurs salons (ancien /alerte),
    on retourne le premier — la prochaine validation /botconfig collapse
    automatiquement vers un seul salon.
    """
    guild = _load_all().get(guild_id, {})
    dests = guild.get("topics", {}).get(topic, {})
    if not dests:
        return None
    channel_id, info = next(iter(dests.items()))
    return {
        "channel_id": channel_id,
        "is_thread": info.get("is_thread", False),
        "role": info.get("role"),
    }


def set_topic_destination(
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
    dicts vides, comme unsubscribe).
    """
    data = _load_all()

    if channel_id is None:
        guild = data.get(guild_id)
        if guild:
            topics = guild.get("topics", {})
            topics.pop(topic, None)
            if not topics:
                data.pop(guild_id, None)
        _save_all(data)
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
    _save_all(data)


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
