# -*- coding: utf-8 -*-
"""Moteur de publication MONO-message persistant (raids, donjons).

UN message par abonné, supprimé puis reposté quand son contenu change. Le
repost (et non l'édition) déclenche une notification : le ping rôle est
injecté DANS la vue (cf. send_view). `ping=False` (refresh manuel) reposte
sans re-notifier, exception assumée à la règle « repost = ping ».

`state` est une fabrique renvoyant un état indexé par (serveur, topic) :
get / set(message_id, content_hash) / purge / invalidate(topic) / save, soit
l'interface de WeeklyMessageState.

Cache d'images : `publish` ne purge PAS (raids et donjons partagent un dossier
de cache, purgé une seule fois par l'orchestrateur du reset) ; `refresh` purge
avant de republier, puisque « forcer » = régénérer les images."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from bot.core.logger import log
from bot.publishing.primitives import (
    config_destination,
    delete_message,
    iter_destinations,
    message_exists,
    send_view,
)
from bot.publishing.repost import Payload


@dataclass
class SingleTopic:
    topic: str
    tag: str  # préfixe des logs, ex. "Raids"
    state: Callable[[], Any]
    payload: Callable[[bool], Awaitable[Optional[Payload]]]
    build_view: Callable[[Any], Awaitable[tuple]]  # data → (vue, fichiers) NEUFS
    purge_cache: Optional[Callable[[], None]] = None
    on_published: Optional[Callable[[Payload], None]] = None

    async def publish(self, bot, *, ping: bool = True, strict: bool = False) -> None:
        """Saute un serveur dont le message est connu et le hash inchangé ;
        sinon supprime l'ancien message et reposte."""
        payload = await self.payload(strict)
        if payload is None:
            return
        state = self.state()
        for guild_id, guild, dest, info in iter_destinations(bot, self.topic):
            saved = state.get(guild_id, self.topic)
            message_id = saved.get("message_id")
            if message_id and saved.get("hash") == payload.hash:
                continue  # contenu inchangé → rien à faire

            await delete_message(dest, message_id)
            view, files = await self.build_view(payload.data)
            new_id = await send_view(dest, view, files, role_id=info.get("role"), ping=ping)
            if new_id:
                state.set(guild_id, self.topic, message_id=new_id, content_hash=payload.hash)
                state.save()
                log.info(f"[{self.tag}] Message publié dans {guild.name}.")

        if self.on_published:
            self.on_published(payload)
        state.save()

    async def restore(self, bot) -> None:
        """Republie SANS ping les messages connus qui n'existent plus. Fetch
        paresseux (aucun fetch si rien ne manque). Ne purge PAS le cache."""
        state = self.state()
        missing = []
        for guild_id, guild, dest, _ in iter_destinations(bot, self.topic):
            mid = state.get(guild_id, self.topic).get("message_id")
            if not mid:
                continue  # jamais publié → géré au reset / à l'ajout
            if not await message_exists(dest, mid):
                missing.append((guild_id, guild, dest))
        if not missing:
            return

        payload = await self.payload(False)
        if payload is None:
            return
        for guild_id, guild, dest in missing:
            view, files = await self.build_view(payload.data)
            new_id = await send_view(dest, view, files)
            if new_id:
                state.set(guild_id, self.topic, message_id=new_id, content_hash=payload.hash)
                log.info(f"[{self.tag}] Message restauré dans {guild.name}.")
        state.save()

    async def on_added(self, bot, guild_id, info: dict) -> None:
        """Publie (avec ping) dans un salon configuré via /botconfig.
        `info` = {channel_id, is_thread, role_id}. Ne purge PAS le cache."""
        target = config_destination(bot, guild_id, info)
        if target is None:
            return
        payload = await self.payload(False)
        if payload is None:
            return
        guild, dest = target
        state = self.state()

        # Suppression défensive d'un éventuel ancien message mémorisé.
        await delete_message(dest, state.get(guild_id, self.topic).get("message_id"))
        view, files = await self.build_view(payload.data)
        mid = await send_view(dest, view, files, role_id=info.get("role_id"), ping=True)
        if mid:
            state.set(guild_id, self.topic, message_id=mid, content_hash=payload.hash)
            state.save()
            log.info(f"[{self.tag}] Message publié dans {guild.name} (nouveau salon).")

    async def on_removed(self, bot, guild_id, info: dict) -> None:
        state = self.state()
        target = config_destination(bot, guild_id, info)
        if target is not None:
            await delete_message(target[1], state.get(guild_id, self.topic).get("message_id"))
        state.purge(guild_id, self.topic)
        state.save()

    async def refresh(self, bot) -> None:
        """/refresh : invalide, purge le cache d'images puis republie SANS ping."""
        self.state().invalidate(self.topic)
        if self.purge_cache:
            self.purge_cache()
        await self.publish(bot, ping=False)
