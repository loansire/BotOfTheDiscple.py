# -*- coding: utf-8 -*-
"""Store d'abonnement générique (par 'topic'), réutilisable maintenance/news.
Règle : 1 topic = au plus 1 channel OU 1 thread par serveur."""
import json

from bot.config import ALERTS_DIR


def _path(topic: str):
    return ALERTS_DIR / f"{topic}.json"


def load_subscriptions(topic: str) -> dict:
    p = _path(topic)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_subscriptions(topic: str, data: dict):
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(_path(topic), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def subscribe(
    topic: str,
    guild_id: str,
    channel_id: str,
    is_thread: bool,
    role_id: str | None = None,
) -> bool:
    """Abonne un salon à un topic.

    Règle : 1 topic = au plus 1 destination par serveur. Si le serveur a déjà
    un salon/thread configuré pour ce topic, l'abonnement est REFUSÉ (il faut
    se désabonner d'abord). Renvoie True si abonné, False si déjà abonné.
    `role_id` (optionnel) = rôle à mentionner lors des annonces.
    """
    data = load_subscriptions(topic)
    if data.get(guild_id, {}).get("channels"):
        return False  # déjà une destination pour ce topic
    key = "thread_ID" if is_thread else "channel_ID"
    data[guild_id] = {"channels": {key: channel_id}, "roles": role_id}
    save_subscriptions(topic, data)
    return True


def current_destination(topic: str, guild_id: str) -> str | None:
    """ID du salon/thread déjà abonné pour ce topic (ou None)."""
    channels = load_subscriptions(topic).get(guild_id, {}).get("channels", {})
    return channels.get("channel_ID") or channels.get("thread_ID")

def unsubscribe(topic: str, guild_id: str, channel_id: str, is_thread: bool) -> bool:
    data = load_subscriptions(topic)
    if guild_id not in data:
        return False
    channels = data[guild_id].get("channels", {})
    key = "thread_ID" if is_thread else "channel_ID"
    removed = channels.pop(key, None) == channel_id
    if not channels:
        data.pop(guild_id, None)
    save_subscriptions(topic, data)
    return removed