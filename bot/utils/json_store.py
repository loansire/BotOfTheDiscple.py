# -*- coding: utf-8 -*-
"""Bases communes des états persistés en JSON (Ressources/AlertDatabase).

- JsonStore          : `_data` dict, chargement tolérant (JSON corrompu →
  état vide + warning, au lieu d'empêcher le cog de charger) et sauvegarde
  ATOMIQUE (cf. bot.utils.jsonio).
- MultiMessageState  : N messages jetables par serveur + hash de contenu
  (Ada-1, Eververse).
- SingleMessageState : 1 message édité en place par serveur + hash
  (Défis ascendants, Distorsion).
"""
from __future__ import annotations

from pathlib import Path

from bot.utils.jsonio import load_json, save_json


class JsonStore:
    # Clés héritées d'anciens formats, purgées au chargement.
    _OBSOLETE_KEYS: tuple[str, ...] = ()

    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}
        self.load()

    def load(self):
        data = load_json(self.path, {})
        self._data = data if isinstance(data, dict) else {}
        for key in self._OBSOLETE_KEYS:
            self._data.pop(key, None)

    def save(self):
        save_json(self.path, self._data)


class MultiMessageState(JsonStore):
    """{ "guilds": { "<guild_id>": { "message_ids": [...], "hash": "..." } } }

    Les messages sont JETABLES : supprimés puis republiés à chaque changement
    de contenu (repost → notification + ping rôle)."""

    # Le dernier reset vit désormais dans PipelineState.
    _OBSOLETE_KEYS = ("last_reset",)

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
        """Oublie tout l'état d'un serveur (retrait du salon)."""
        self._data.get("guilds", {}).pop(str(guild_id), None)

    def invalidate(self):
        """Efface les hashes pour forcer un repost au prochain publish.

        Les IDs sont CONSERVÉS : le handler en a besoin pour supprimer les
        anciens messages avant repost. Utilisé par /refresh."""
        for guild_id in list(self._data.get("guilds", {})):
            self.set(guild_id, content_hash="")


class SingleMessageState(JsonStore):
    """{ "<guild_id>": { "message_id": "...", "hash": "..." } }

    On ne persiste que l'id du message publié et un `hash` identifiant la
    période affichée : s'il diffère de la période courante, le message est
    édité (avance d'un cran)."""

    def get(self, guild_id) -> dict:
        """Entrée d'un serveur ({message_id, hash}), valeurs None si absent."""
        return self._data.get(str(guild_id), {"message_id": None, "hash": None})

    def set(self, guild_id, *, message_id, content_hash) -> None:
        self._data[str(guild_id)] = {
            "message_id": str(message_id),
            "hash": content_hash,
        }

    def purge(self, guild_id) -> None:
        """Oublie l'état d'un serveur (retrait du salon)."""
        self._data.pop(str(guild_id), None)

    def invalidate(self) -> None:
        """Efface les hash (conserve les message_id) → force une ré-édition au
        prochain publish. Le caller appelle save()."""
        for entry in self._data.values():
            entry["hash"] = None
