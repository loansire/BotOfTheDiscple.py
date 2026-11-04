# -*- coding: utf-8 -*-
"""État des messages persistants Xûr (bot/storage/messages.py, topic `xur`).

Deux rôles de message distincts par guild :
- `status_id`   (slot 'status')  : le message « Xûr est là / n'est pas là » —
  PERSISTANT entre arrivée et départ. Supprimé+reposté à l'arrivée (vendredi) ;
  édité in-place au départ (mardi).
- `category_ids` (slot 'content') : les messages catégories (+ ping) —
  JETABLES. Supprimés puis republiés chaque vendredi, supprimés le mardi.

Le dernier reset traité ne vit PAS ici : la pipeline en détient l'unique
source de vérité (PipelineState).
"""
from functools import cache

from bot.storage.base import flush
from bot.storage.messages import CONTENT, Entry, messages

TOPIC = "xur"
_STATUS = "status"


class XurMessageState:
    # -- Lecture -------------------------------------------------------
    def get(self, guild_id) -> dict:
        """Entrée normalisée d'un guild :
        {status_id: str|None, category_ids: [...], hash: str}."""
        entry = messages.get(guild_id, TOPIC)
        if entry is None:
            return {"status_id": None, "category_ids": [], "hash": ""}
        status = entry.slots.get(_STATUS, [])
        return {
            "status_id": status[0] if status else None,
            "category_ids": list(entry.slots.get(CONTENT, [])),
            "hash": entry.hash or "",
        }

    def status_id(self, guild_id) -> str | None:
        return self.get(guild_id)["status_id"]

    def category_ids(self, guild_id) -> list:
        return list(self.get(guild_id)["category_ids"])

    def content_hash(self, guild_id) -> str:
        return self.get(guild_id)["hash"]

    def iter_guilds(self):
        """Itère (guild_id, entry_normalisée) pour tous les guilds connus."""
        for guild_id in messages.guilds(TOPIC):
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
        new_cats = list(category_ids) if category_ids is not None else current["category_ids"]
        new_hash = content_hash if content_hash is not None else current["hash"]
        slots = {CONTENT: [str(i) for i in new_cats]}
        if new_status:
            slots[_STATUS] = [str(new_status)]
        messages.put(guild_id, TOPIC, Entry(slots=slots, hash=new_hash))

    def clear_categories(self, guild_id):
        """Vide la liste des messages catégories (après suppression Discord)."""
        self.set(guild_id, category_ids=[])

    def purge(self, guild_id):
        """Oublie tout l'état Xûr d'un serveur (retrait du salon)."""
        messages.drop(guild_id, TOPIC)

    async def invalidate(self):
        """Efface les hashes pour forcer un repost au prochain publish.

        Les IDs (status + catégories) sont CONSERVÉS : le handler en a besoin
        pour éditer/supprimer les anciens messages avant repost. Utilisé par
        /refresh."""
        for guild_id in messages.guilds(TOPIC):
            self.set(guild_id, content_hash="")
        await self.save()

    async def save(self) -> None:
        await flush()


@cache
def xur_state() -> XurMessageState:
    """Instance UNIQUE partagée."""
    return XurMessageState()
