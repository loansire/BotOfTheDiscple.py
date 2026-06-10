# -*- coding: utf-8 -*-
"""État des messages persistants weekly/daily.

Sépare l'état runtime (quel message ai-je posté, et quel était son contenu)
de la configuration déclarative (subscriptions.json). Fichier unique :

{
  "guilds": {
    "<guild_id>": {
      "<topic>": { "message_id": "...", "hash": "..." }
    }
  },
  "last_reset": "<iso>"   # dernier reset quotidien déjà traité
}

Le `hash` évite de reposter un message dont le contenu n'a pas changé
(le tableau raids/donjons est statique ; les secteurs changent chaque jour).
Le refresh manuel passe par `invalidate()` pour forcer un repost.
"""
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "weekly_messages.json"


class WeeklyMessageState:
    def __init__(self, path=STATE_PATH):
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # ── Messages persistants ──────────────────────────────────────────
    def get(self, guild_id, topic: str) -> dict:
        return (
            self._data.get("guilds", {})
            .get(str(guild_id), {})
            .get(topic, {})
        )

    def set(self, guild_id, topic: str, *, message_id: str, content_hash: str):
        guilds = self._data.setdefault("guilds", {})
        guild = guilds.setdefault(str(guild_id), {})
        guild[topic] = {"message_id": message_id, "hash": content_hash}

    def invalidate(self):
        """Efface tous les hashes pour forcer un repost au prochain publish.

        Les `message_id` sont CONSERVÉS : le publisher en a besoin pour
        supprimer les anciens messages avant de reposter. Utilisé par le
        refresh manuel (/weekly-refresh)."""
        for guild in self._data.get("guilds", {}).values():
            for topic_data in guild.values():
                topic_data.pop("hash", None)
        self.save()

    # ── Dernier reset traité ──────────────────────────────────────────
    @property
    def last_reset_iso(self) -> str:
        return self._data.get("last_reset", "")

    @last_reset_iso.setter
    def last_reset_iso(self, value: str):
        self._data["last_reset"] = value