# -*- coding: utf-8 -*-
"""Moteur de publication MULTI-message « jetable » : supprime puis republie.

Utilisé par Ada-1, Eververse, l'Avant-garde et les secteurs oubliés. Par
serveur abonné : N messages de contenu (Components V2), puis un message de
ping rôle SEUL en dernier (si un rôle est défini). Le ping est rangé avec les
messages de contenu (message_ids) → supprimé/reposté avec eux.

Chaque feature ne déclare que ce qui lui est propre (cf. RepostTopic) :
- `payload(strict)` : fetch + hash du contenu, ou None si rien à publier ;
- `build_views(data)` : liste de (vue, fichiers) NEUFS ;
- `purge_cache()` : purge du cache d'images à SA cadence (publication seule) ;
- `on_published(payload)` : mémorisation post-publication (garde-fou fraîcheur).

Cycle de vie partagé :
- publish    : reset (ou /refresh avec ping=False). Saute un serveur déjà à
  jour (même hash + messages présents). `strict` est transmis au payload.
- restore    : répare (sans ping) les serveurs dont un message a disparu. Fetch
  paresseux : aucun appel API si rien ne manque. Ne purge PAS le cache.
- on_added   : publication immédiate dans un salon configuré via /botconfig.
- on_removed : suppression des messages d'un salon retiré + purge de l'état.
- refresh    : invalide l'état puis republie SANS ping.

Phase fetch isolée : un payload None → on ne touche à rien. Une
BungieUnavailableError levée par le payload remonte (hold mode de la pipeline).

`state` est une fabrique renvoyant un état à l'interface MultiMessageState
(get / set / purge / invalidate / iter_guilds / save)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from bot.core.logger import log
from bot.publishing.primitives import (
    all_exist,
    config_destination,
    delete_messages,
    destinations_by_guild,
    iter_destinations,
    send_ping,
    send_view,
)

ViewList = list  # [(discord.ui.LayoutView, list[discord.File]), ...]


@dataclass(frozen=True)
class Payload:
    """Contenu prêt à publier : données métier + hash (+ signature éventuelle
    pour le garde-fou « données pas prêtes »)."""

    data: Any
    hash: str
    sig: list[str] = field(default_factory=list)


@dataclass
class RepostTopic:
    topic: str
    tag: str  # préfixe des logs, ex. "Ada-1"
    state: Callable[[], Any]
    payload: Callable[[bool], Awaitable[Optional[Payload]]]
    build_views: Callable[[Any], Awaitable[ViewList]]
    purge_cache: Optional[Callable[[], None]] = None
    on_published: Optional[Callable[[Payload], None]] = None
    # Loggué (warning) quand publish n'a rien à publier ; None = silencieux.
    empty_warning: Optional[str] = None

    # ── Republication d'un serveur ────────────────────────────────────

    async def _repost(self, guild, dest, payload: Payload, role_id, *, ping: bool) -> None:
        """Supprime tout (contenu + ancien ping) puis republie le contenu, suivi
        du ping rôle SEUL en dernier (si demandé et rôle défini)."""
        state = self.state()
        guild_id = str(guild.id)
        await delete_messages(dest, state.get(guild_id)["message_ids"])

        new_ids: list = []
        views = await self.build_views(payload.data)
        for view, files in views:
            mid = await send_view(dest, view, files)
            if mid:
                new_ids.append(mid)
        sent = len(new_ids)
        content_hash = payload.hash
        # Envoi partiel → hash vide : le serveur sera retenté au prochain publish
        # au lieu d'être considéré à jour avec un message manquant.
        if sent < len(views):
            log.warning(f"[{self.tag}] {sent}/{len(views)} message(s) envoyé(s) dans {guild.name}.")
            content_hash = ""

        if ping:
            ping_id = await send_ping(dest, role_id)
            if ping_id:
                new_ids.append(ping_id)

        state.set(guild_id, message_ids=new_ids, content_hash=content_hash)
        log.info(f"[{self.tag}] {sent} message(s) publié(s) dans {guild.name}.")

    # ── Cycle de vie ──────────────────────────────────────────────────

    async def publish(self, bot, *, ping: bool = True, strict: bool = False) -> None:
        payload = await self.payload(strict)
        if payload is None:
            if self.empty_warning:
                log.warning(f"[{self.tag}] {self.empty_warning}")
            return
        if self.purge_cache:
            # Une fois le fetch confirmé, AVANT toute régénération : on ne
            # supprime jamais une image qu'on vient de composer.
            self.purge_cache()

        state = self.state()
        for guild_id, guild, dest, info in iter_destinations(bot, self.topic):
            saved = state.get(guild_id)
            if saved["hash"] == payload.hash and saved["message_ids"]:
                continue  # déjà publié pour cette période
            await self._repost(guild, dest, payload, info.get("role"), ping=ping)

        if self.on_published:
            self.on_published(payload)
        state.save()

    async def restore(self, bot) -> None:
        """Serveur déjà publié dont un message manque → tout le serveur est
        reconstruit (plus simple et fiable), sans ping."""
        state = self.state()
        dests = destinations_by_guild(bot, self.topic)
        payload: Optional[Payload] = None
        fetched = False

        for guild_id, entry in state.iter_guilds():
            if guild_id not in dests:
                continue
            guild, dest = dests[guild_id]
            ids = entry["message_ids"]
            if ids and await all_exist(dest, ids):
                continue  # tout est en place

            if not fetched:
                payload = await self.payload(False)
                fetched = True
            if payload is None:
                continue  # fetch impossible → laissé au hold mode
            await self._repost(guild, dest, payload, None, ping=False)

        state.save()

    async def on_added(self, bot, guild_id, info: dict) -> None:
        """`info` = {channel_id, is_thread, role_id} (forme /botconfig)."""
        target = config_destination(bot, guild_id, info)
        if target is None:
            return
        payload = await self.payload(False)
        if payload is None:
            return
        guild, dest = target
        await self._repost(guild, dest, payload, info.get("role_id"), ping=True)
        self.state().save()

    async def on_removed(self, bot, guild_id, info: dict) -> None:
        state = self.state()
        target = config_destination(bot, guild_id, info)
        if target is not None:
            await delete_messages(target[1], state.get(guild_id)["message_ids"])
        state.purge(guild_id)
        state.save()

    async def refresh(self, bot) -> None:
        """/refresh : force le repost (les IDs sont conservés pour supprimer les
        anciens messages), SANS ping."""
        self.state().invalidate()
        await self.publish(bot, ping=False)
