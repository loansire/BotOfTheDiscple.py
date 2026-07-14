# -*- coding: utf-8 -*-
"""État des messages persistants Eververse.

Un seul rôle de message : les 3 messages de sections (principales / autres /
Argentum), stockés à plat par guild. JETABLES : supprimés puis republiés à
chaque changement de contenu (repost → notification + ping rôle).

{
  "guilds": {
    "<guild_id>": {
      "message_ids": ["...", "...", "..."],
      "hash": "..."
    }
  }
}

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique source
de vérité (PipelineState). Une éventuelle clé `last_reset` héritée est purgée au
chargement.

Le `hash` (calculé par le handler : id de reset + itemHash) évite de reposter un
contenu inchangé. Le refresh manuel passe par `invalidate()` ; le retrait d'un
salon via /botconfig passe par `purge()`."""
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "eververse_messages.json"


class EververseMessageState:
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

    # ── Lecture ───────────────────────────────────────────────────────
    def _raw(self, guild_id) -> dict:
        return self._data.get("guilds", {}).get(str(guild_id), {})

    def get(self, guild_id) -> dict:
        """Entrée normalisée : {message_ids: [...], hash: str}."""
        entry = self._raw(guild_id)
        return {
            "message_ids": list(entry.get("message_ids", [])),
            "hash": entry.get("hash", ""),
        }

    def message_ids(self, guild_id) -> list:
        return list(self.get(guild_id)["message_ids"])

    def content_hash(self, guild_id) -> str:
        return self.get(guild_id)["hash"]

    def iter_guilds(self):
        """Itère (guild_id, entry_normalisée) pour tous les guilds connus."""
        for guild_id in list(self._data.get("guilds", {})):
            yield guild_id, self.get(guild_id)

    # ── Écriture ──────────────────────────────────────────────────────
    def set(self, guild_id, *, message_ids=None, content_hash=None):
        """Met à jour sélectivement les champs fournis (les autres conservés)."""
        current = self.get(guild_id)
        new_ids = list(message_ids) if message_ids is not None else current["message_ids"]
        new_hash = content_hash if content_hash is not None else current["hash"]
        guilds = self._data.setdefault("guilds", {})
        guilds[str(guild_id)] = {"message_ids": new_ids, "hash": new_hash}

    def purge(self, guild_id):
        """Oublie tout l'état Eververse d'un serveur (retrait du salon)."""
        self._data.get("guilds", {}).pop(str(guild_id), None)

    def invalidate(self):
        """Efface les hashes pour forcer un repost au prochain publish.

        Les IDs sont CONSERVÉS : le handler en a besoin pour supprimer les
        anciens messages avant repost. Utilisé par /refresh-all."""
        for guild_id in list(self._data.get("guilds", {})):
            self.set(guild_id, content_hash="")
        self.save()