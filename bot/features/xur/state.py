# -*- coding: utf-8 -*-
"""État des messages persistants Xûr.

Deux rôles de message distincts par guild :
- `status_id`   : le message « Xûr est là / n'est pas là » — PERSISTANT entre
  arrivée et départ. Supprimé+reposté à l'arrivée (vendredi) ; édité in-place
  au départ (mardi).
- `category_ids`: les 3 messages catégories (Armes / Armures / Matériaux) —
  JETABLES. Supprimés puis republiés chaque vendredi, supprimés le mardi.

{
  "guilds": {
    "<guild_id>": {
      "status_id": "...",
      "category_ids": ["...", "...", "..."],
      "hash": "..."
    }
  }
}

Le dernier reset traité ne vit PLUS ici : la pipeline en détient l'unique
source de vérité (PipelineState). Une éventuelle clé `last_reset` héritée d'un
ancien fichier est purgée au chargement.

Rétro-compatibilité : l'ancien schéma stockait une liste plate `message_ids`.
À la lecture, on la convertit (1er ID → status_id, reste → category_ids) pour
ne pas casser au redémarrage après mise à jour.
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
        # Clé obsolète (le dernier reset vit désormais dans PipelineState).
        self._data.pop("last_reset", None)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # -- Lecture (avec normalisation rétro-compatible) -----------------
    def _raw(self, guild_id) -> dict:
        return self._data.get("guilds", {}).get(str(guild_id), {})

    def get(self, guild_id) -> dict:
        """Entrée normalisée d'un guild :
        {status_id: str|None, category_ids: [...], hash: str}.

        Convertit à la volée l'ancien format `message_ids` (liste plate)."""
        entry = self._raw(guild_id)
        if not entry:
            return {"status_id": None, "category_ids": [], "hash": ""}

        if "message_ids" in entry and "status_id" not in entry:
            # Ancien format : 1er = statut, reste = catégories.
            old = list(entry.get("message_ids", []))
            status_id = old[0] if old else None
            category_ids = old[1:] if len(old) > 1 else []
        else:
            status_id = entry.get("status_id")
            category_ids = list(entry.get("category_ids", []))

        return {
            "status_id": status_id,
            "category_ids": category_ids,
            "hash": entry.get("hash", ""),
        }

    def status_id(self, guild_id) -> str | None:
        return self.get(guild_id)["status_id"]

    def category_ids(self, guild_id) -> list:
        return list(self.get(guild_id)["category_ids"])

    def content_hash(self, guild_id) -> str:
        return self.get(guild_id)["hash"]

    def iter_guilds(self):
        """Itère (guild_id, entry_normalisée) pour tous les guilds connus."""
        for guild_id in list(self._data.get("guilds", {})):
            yield guild_id, self.get(guild_id)

    # -- Écriture ------------------------------------------------------
    def set(
        self,
        guild_id,
        *,
        status_id: str | None = None,
        category_ids: list | None = None,
        content_hash: str | None = None,
    ):
        """Met à jour sélectivement les champs fournis (les autres sont
        conservés depuis l'état normalisé existant)."""
        current = self.get(guild_id)
        new_status = status_id if status_id is not None else current["status_id"]
        new_cats = (
            list(category_ids) if category_ids is not None else current["category_ids"]
        )
        new_hash = content_hash if content_hash is not None else current["hash"]

        guilds = self._data.setdefault("guilds", {})
        guilds[str(guild_id)] = {
            "status_id": new_status,
            "category_ids": new_cats,
            "hash": new_hash,
        }

    def clear_categories(self, guild_id):
        """Vide la liste des messages catégories (après suppression Discord)."""
        self.set(guild_id, category_ids=[])

    def purge(self, guild_id):
        """Oublie tout l'état Xûr d'un serveur (retrait du salon)."""
        self._data.get("guilds", {}).pop(str(guild_id), None)

    def invalidate(self):
        """Efface les hashes pour forcer un repost au prochain publish.

        Les IDs (status + catégories) sont CONSERVÉS : le handler en a besoin
        pour éditer/supprimer les anciens messages avant repost. Utilisé par
        /refresh-all."""
        for guild_id in list(self._data.get("guilds", {})):
            self.set(guild_id, content_hash="")
        self.save()