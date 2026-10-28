# -*- coding: utf-8 -*-
"""Publication par ÉDITION EN PLACE (un message par serveur, édité à chaque
nouvelle période) — partagée par les Défis ascendants et la Distorsion.

- AUCUN ping (l'édition ne notifie pas ; ces topics n'exposent pas de rôle) ;
- le message garde sa position dans le salon ;
- idempotent grâce au `content_hash` : un salon déjà à jour est ignoré ;
- rattrapage (période changée pendant une coupure) et réparation (message
  supprimé à la main → renvoi d'un message neuf).

Le hash n'est enregistré QUE si l'édition/l'envoi a réussi : sur une erreur
transitoire (rate-limit, 5xx, permissions), l'id est conservé mais le hash est
vidé, pour que le prochain tick retente au lieu de croire le salon à jour.

Chaque feature déclare un EditInPlaceTopic :
- `build(now, ctx)` → (vue, fichiers NEUFS) ; `chash(now, ctx)` → hash ;
- `context(now)` (optionnel, async) : donnée live résolue une fois par
  publication (ex. contrat de Petra), passée à build/chash ;
- `reset_context()` (optionnel) : oublie la donnée live mémoïsée (/refresh)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

import discord

from bot.core.logger import log
from bot.publishing.primitives import config_destination, delete_message, iter_destinations

# Factory renvoyant une vue NEUVE (et ses fichiers) à chaque appel : un
# discord.File est consommé après envoi.
ViewFactory = Callable[[], tuple[discord.ui.LayoutView, list[discord.File]]]


async def _send(dest, build: ViewFactory, tag: str) -> str | None:
    """Envoie un message neuf (Components V2, sans contenu → aucun ping)."""
    view, files = build()
    try:
        sent = await dest.send(view=view, files=files)
        return str(sent.id)
    except discord.DiscordException as e:
        log.error(f"[{tag}] Envoi échoué dans {dest} : {e}")
        return None


async def _edit(dest, message_id: str, build: ViewFactory, tag: str) -> tuple[str | None, bool]:
    """Édite le message existant → (id, succès).

    (None, False) : le message a disparu → le caller renvoie un message neuf.
    (id, False)   : échec transitoire → id conservé, nouvelle tentative plus tard."""
    view, files = build()
    try:
        msg = await dest.fetch_message(int(message_id))
        await msg.edit(attachments=files, view=view)
        return message_id, True
    except discord.NotFound:
        return None, False
    except discord.DiscordException as e:
        log.warning(f"[{tag}] Édition échouée ({message_id}) : {e}")
        return message_id, False


@dataclass
class EditInPlaceTopic:
    topic: str
    tag: str
    state: Callable[[], Any]  # → SingleMessageState
    build: Callable[[datetime, Any], tuple]
    chash: Callable[[datetime, Any], str]
    context: Optional[Callable[[datetime], Awaitable[Any]]] = None
    reset_context: Optional[Callable[[], None]] = None
    # Sérialise le poll à la minute et /refresh (qui tourne sous le verrou de
    # la pipeline, pas sous celui du cog des rotations).
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def _snapshot(self) -> tuple[ViewFactory, str]:
        """(fabrique de vue, hash) figés sur l'instant courant."""
        now = datetime.now(timezone.utc)
        ctx = await self.context(now) if self.context else None
        return (lambda: self.build(now, ctx)), self.chash(now, ctx)

    async def publish(self, bot, *, force: bool = False) -> None:
        """Met à jour tous les salons abonnés. `force=True` réédite même si le
        hash est identique (/refresh)."""
        async with self._lock:
            await self._publish(bot, force=force)

    async def _publish(self, bot, *, force: bool) -> None:
        build, chash = await self._snapshot()
        state = self.state()
        edited, sent = 0, 0

        for guild_id, _, dest, _ in iter_destinations(bot, self.topic):
            saved = state.get(guild_id)
            message_id = saved.get("message_id")
            if not force and message_id and saved.get("hash") == chash:
                continue  # déjà à jour pour cette période

            new_id, ok = (None, False)
            if message_id:
                new_id, ok = await _edit(dest, message_id, build, self.tag)
                edited += ok
            if new_id is None:
                # (pas d'id connu, ou message disparu) → message neuf
                new_id = await _send(dest, build, self.tag)
                ok = new_id is not None
                sent += ok

            if new_id:
                state.set(guild_id, message_id=new_id, content_hash=chash if ok else None)

        if edited or sent:
            state.save()
            log.info(f"[{self.tag}] {edited} message(s) édité(s), {sent} envoyé(s) ({chash}).")

    async def refresh(self, bot) -> None:
        """/refresh : ré-édition forcée (sans ping), donnée live re-tirée."""
        if self.reset_context:
            self.reset_context()
        self.state().invalidate()
        await self.publish(bot, force=True)

    async def on_added(self, bot, guild_id, info: dict) -> None:
        """Nouveau salon configuré → publication initiale immédiate."""
        target = config_destination(bot, guild_id, info)
        if target is None:
            return
        build, chash = await self._snapshot()
        new_id = await _send(target[1], build, self.tag)
        if new_id:
            state = self.state()
            state.set(guild_id, message_id=new_id, content_hash=chash)
            state.save()
            log.info(f"[{self.tag}] Message publié dans {target[0].name} (nouveau salon).")

    async def on_removed(self, bot, guild_id, info: dict) -> None:
        """Salon retiré → suppression du message + purge de l'état."""
        state = self.state()
        target = config_destination(bot, guild_id, info)
        if target is not None:
            await delete_message(target[1], state.get(guild_id).get("message_id"))
        state.purge(guild_id)
        state.save()
