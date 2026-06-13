# -*- coding: utf-8 -*-
"""État des messages persistants Xûr (multi-message).

Xûr peut occuper PLUSIEURS messages (limite Discord : 10 images/message).
Le state mémorise donc une LISTE de message_id par guild, plus un hash de
contenu pour éviter de reposter à l'identique.

{
  "guilds": {
    "<guild_id>": { "message_ids": ["...", "..."], "hash": "..." }
  },
  "last_reset": "<iso>"   # dernier reset quotidien déjà traité
}

La publication multi-message est gérée dans le cog (pas par
publish_persistent_view, qui est mono-message). Le mardi, le cog édite le
PREMIER message (« Xûr est parti ») et supprime les autres.
"""
import json

from bot.config import ALERTS_DIR

STATE_PATH = ALERTS_DIR / "xur_messages.json"

TOPIC = "xur"


class XurMessageState:
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

    # -- Messages persistants ------------------------------------------
    def get(self, guild_id) -> dict:
        """Entrée d'un guild : {message_ids: [...], hash: ...} ou {}."""
        return self._data.get("guilds", {}).get(str(guild_id), {})

    def get_message_ids(self, guild_id) -> list:
        return list(self.get(guild_id).get("message_ids", []))

    def set(self, guild_id, *, message_ids: list, content_hash: str):
        guilds = self._data.setdefault("guilds", {})
        guilds[str(guild_id)] = {
            "message_ids": list(message_ids),
            "hash": content_hash,
        }

    def iter_guilds(self):
        """Itère (guild_id, entry) pour tous les guilds ayant des messages."""
        for guild_id, entry in self._data.get("guilds", {}).items():
            yield guild_id, entry

    def invalidate(self):
        """Efface les hashes pour forcer un repost au prochain publish.

        Les message_ids sont CONSERVÉS (le cog en a besoin pour supprimer les
        anciens messages avant repost). Utilisé par /xur-reset."""
        for entry in self._data.get("guilds", {}).values():
            entry.pop("hash", None)
        self.save()

    # -- Dernier reset traité ------------------------------------------
    @property
    def last_reset_iso(self) -> str:
        return self._data.get("last_reset", "")

    @last_reset_iso.setter
    def last_reset_iso(self, value: str):
        self._data["last_reset"] = value