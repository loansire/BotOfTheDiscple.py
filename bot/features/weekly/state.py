# -*- coding: utf-8 -*-
"""État des messages persistants weekly/daily.

Sépare l'état runtime (quel(s) message(s) ai-je posté, et quel était leur
contenu) de la configuration déclarative (subscriptions.json). Fichier :

{
  "guilds": {
    "<guild_id>": {
      "<topic>": { "message_id": "...", "hash": "..." }          # topic mono-message
      "<topic>": { "message_ids": ["...", ...], "hash": "..." }  # topic multi-message
    }
  }
}

Deux formes coexistent par topic :
- mono-message (raids, donjons) : { "message_id", "hash" } via set().
- multi-message (secteurs oubliés) : { "message_ids", "hash" } via set_ids().
Le lecteur récupère le dict brut avec get() et lit la clé adaptée au topic.

Le dernier reset traité ne vit PLUS ici : la pipeline en détient l'unique
source de vérité (PipelineState). Une éventuelle clé `last_reset` héritée d'un
ancien fichier est purgée au chargement.

Le `hash` évite de reposter un message dont le contenu n'a pas changé. Le
refresh manuel passe par `invalidate()`. Le retrait d'un salon via /botconfig
passe par `purge()`.
"""
from bot.config import ALERTS_DIR
from bot.utils.json_store import JsonStore

STATE_PATH = ALERTS_DIR / "weekly_messages.json"


class WeeklyMessageState(JsonStore):
    _OBSOLETE_KEYS = ('last_reset',)

    def __init__(self, path=STATE_PATH):
        super().__init__(path)

    # ── Messages persistants ──────────────────────────────────────────
    def get(self, guild_id, topic: str) -> dict:
        return (
            self._data.get("guilds", {})
            .get(str(guild_id), {})
            .get(topic, {})
        )

    def set(self, guild_id, topic: str, *, message_id: str, content_hash: str):
        """Topic MONO-message (raids/donjons) : un seul message_id."""
        guilds = self._data.setdefault("guilds", {})
        guild = guilds.setdefault(str(guild_id), {})
        guild[topic] = {"message_id": message_id, "hash": content_hash}

    def set_ids(self, guild_id, topic: str, *, message_ids: list, content_hash: str):
        """Topic MULTI-message (secteurs oubliés) : liste de message_ids.

        Remplace intégralement l'entrée du topic (l'éventuelle clé mono-message
        `message_id` héritée disparaît donc naturellement)."""
        guilds = self._data.setdefault("guilds", {})
        guild = guilds.setdefault(str(guild_id), {})
        guild[topic] = {"message_ids": list(message_ids), "hash": content_hash}

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

    # ── Signatures de contenu (garde-fou données périmées) ────────────
    def last_signature(self, topic: str) -> dict:
        """Dernier contenu publié pour un topic, tous serveurs confondus :
        {"period": "<iso début de période>", "sig": [...]} (vide si inconnu)."""
        return self._data.get("signatures", {}).get(topic, {})

    def set_signature(self, topic: str, period_iso: str, sig: list[str]):
        self._data.setdefault("signatures", {})[topic] = {
            "period": period_iso,
            "sig": sorted(sig),
        }

    # ── Défis de la semaine (Avant-garde) ─────────────────────────────
    def week_challenges(self, week_iso: str) -> dict[int, int]:
        """Défis Avant-garde vus pendant la semaine `week_iso` (début = reset
        du mardi) : {activity_hash: arme défi}. Vide pour une autre semaine."""
        saved = self._data.get("vanguard_challenges", {})
        if saved.get("week") != week_iso:
            return {}
        return {int(k): int(v) for k, v in saved.get("items", {}).items()}

    def set_week_challenges(self, week_iso: str, items: dict[int, int]):
        self._data["vanguard_challenges"] = {
            "week": week_iso,
            "items": {str(k): v for k, v in items.items()},
        }

    def invalidate(self, topic: str | None = None):
        """Efface les hashes pour forcer un repost au prochain publish.

        `topic=None` (défaut) → tous les topics (comportement historique,
        utilisé par un refresh global). `topic="weekly_raid"` (par ex.) → ne
        vide QUE le hash de ce topic, laissant les autres intacts : c'est ce
        que veut un refresh ciblé, l'état weekly couvrant 3 topics à la fois.

        Les `message_id` / `message_ids` sont CONSERVÉS : le publisher en a
        besoin pour supprimer les anciens messages avant de reposter."""
        for guild in self._data.get("guilds", {}).values():
            for t, topic_data in guild.items():
                if topic is None or t == topic:
                    topic_data.pop("hash", None)
        self.save()