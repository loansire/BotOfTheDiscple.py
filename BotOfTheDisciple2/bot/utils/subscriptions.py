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


def subscribe(topic: str, guild_id: str, channel_id: str, is_thread: bool):
    data = load_subscriptions(topic)
    guild = data.setdefault(guild_id, {"channels": {}, "roles": None})
    key = "thread_ID" if is_thread else "channel_ID"
    guild["channels"] = {key: channel_id}  # remplace l'éventuel précédent
    save_subscriptions(topic, data)


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