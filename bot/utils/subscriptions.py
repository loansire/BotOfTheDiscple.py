# -*- coding: utf-8 -*-
"""Store d'abonnement générique (par 'topic'), réutilisable maintenance/news.

Modèle : un topic peut être abonné dans PLUSIEURS salons/threads d'un même
serveur. Un salon/thread donné est soit abonné, soit non (toggle).
Format JSON par topic :
{
  "<guild_id>": {
    "<channel_or_thread_id>": {"is_thread": bool, "role": "<role_id>"|null}
  }
}
"""
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
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_subscribed(topic: str, guild_id: str, dest_id: str) -> bool:
    """True si ce salon/thread est déjà abonné à ce topic."""
    return dest_id in load_subscriptions(topic).get(guild_id, {})


def subscribe(topic, guild_id, dest_id, is_thread, role_id=None) -> None:
    """Abonne (ou met à jour) un salon/thread à un topic."""
    data = load_subscriptions(topic)
    data.setdefault(guild_id, {})[dest_id] = {"is_thread": is_thread, "role": role_id}
    save_subscriptions(topic, data)


def unsubscribe(topic, guild_id, dest_id) -> bool:
    """Désabonne un salon/thread. True si un abonnement a été retiré."""
    data = load_subscriptions(topic)
    dests = data.get(guild_id, {})
    removed = dests.pop(dest_id, None) is not None
    if not dests:
        data.pop(guild_id, None)
    save_subscriptions(topic, data)
    return removed