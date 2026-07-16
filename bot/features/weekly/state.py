# -*- coding: utf-8 -*-
"""État des messages persistants weekly/daily.

Sépare l'état runtime (quel message ai-je posté, et quel était son contenu)
de la configuration déclarative (subscriptions.json). Fichier :

{
  "guilds": {
    "<guild_id>": {
      "<topic>": { "message_id": "...", "hash": "..." }
    }
  }
}

Le dernier reset traité ne vit PLUS ici : la pipeline en détient l'unique
source de vérité (PipelineState). Une éventuelle clé `last_reset` héritée d'un
ancien fichier est purgée au chargement.

Le `hash` évite de reposter un message dont le contenu n'a pas changé. Le
refresh manuel passe par `invalidate()`. Le retrait d'un salon via /botconfig
passe par `purge()`.
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
        # Clé obsolète (le dernier reset vit désormais dans PipelineState).
        self._data.pop("last_reset", None)

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

    def purge(self, guild_id, topic: str):
        """Oublie l'état d'un topic pour un serveur (retrait d'un salon).
        Nettoie le dict serveur s'il devient vide."""
        guilds = self._data.get("guilds", {})
        guild = guilds.get(str(guild_id))
        if not guild:
            return
        guild.pop(topic, None)
        if not guild:
            guilds.pop(str(guild_id), None)

    def invalidate(self, topic: str | None = None):
        """Efface les hashes pour forcer un repost au prochain publish.

        `topic=None` (défaut) → tous les topics (comportement historique,
        utilisé par un refresh global). `topic="weekly_raid"` (par ex.) → ne
        vide QUE le hash de ce topic, laissant les autres intacts : c'est ce
        que veut un refresh ciblé, l'état weekly couvrant 3 topics à la fois.

        Les `message_id` sont CONSERVÉS : le publisher en a besoin pour
        supprimer les anciens messages avant de reposter."""
        for guild in self._data.get("guilds", {}).values():
            for t, topic_data in guild.items():
                if topic is None or t == topic:
                    topic_data.pop("hash", None)
        self.save()