# -*- coding: utf-8 -*-
"""Publication par ÉDITION EN PLACE (un message par serveur, édité à chaque
nouvelle version) — partagée par les Défis ascendants et la Distorsion.

Le contenu vient de la base (bot/publishing/content_source.py) : ce moteur ne
calcule rien, il compare le hash de la dernière version au hash publié dans
chaque serveur et édite ce qui est en retard.

- AUCUN ping (l'édition ne notifie pas ; ces topics n'exposent pas de rôle) ;
- le message garde sa position dans le salon ;
- idempotent grâce au hash : un salon déjà à jour est ignoré ;
- rattrapage (version changée pendant une coupure) et réparation (message
  supprimé à la main → renvoi d'un message neuf).

Le hash n'est enregistré QUE si l'édition/l'envoi a réussi : sur une erreur
transitoire (rate-limit, 5xx, permissions), l'id est conservé mais le hash est
vidé, pour que le prochain tick retente au lieu de croire le salon à jour.

`produce` (optionnel) : étape de CALCUL du bot qui produit le contenu
(`force=True` → oublie ses données live mémoïsées). Absente sur un bot qui ne
fait que publier."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

import discord

from bot.core.logger import log
from bot.publishing.content_source import Snapshot, snapshot
from bot.publishing.primitives import config_destination, delete_message, iter_destinations


async def _send(dest, snap: Snapshot, tag: str) -> str | None:
    """Envoie un message neuf (Components V2, sans contenu → aucun ping)."""
    out = snap.render()
    try:
        sent = await dest.send(view=out.view, files=out.files)
        return str(sent.id)
    except discord.DiscordException as e:
        log.error(f"[{tag}] Envoi échoué dans {dest} : {e}")
        return None


async def _edit(dest, message_id: str, snap: Snapshot, tag: str) -> tuple[str | None, bool]:
    """Édite le message existant → (id, succès).

    (None, False) : le message a disparu → le caller renvoie un message neuf.
    (id, False)   : échec transitoire → id conservé, nouvelle tentative plus tard."""
    out = snap.render()
    try:
        msg = await dest.fetch_message(int(message_id))
        await msg.edit(attachments=out.files, view=out.view)
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
    produce: Optional[Callable[[bool], Awaitable[None]]] = None
    # Sérialise le poll à la minute et /refresh (qui tourne sous le verrou de
    # la pipeline, pas sous celui du cog des rotations).
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def _snapshot(self, *, force: bool = False) -> Snapshot | None:
        if self.produce:
            await self.produce(force)
        snap = await snapshot(self.topic)
        if snap is None:
            log.warning(f"[{self.tag}] Aucun contenu en base : rien à publier.")
        return snap

    async def publish(self, bot, *, force: bool = False) -> None:
        """Met à jour tous les salons abonnés. `force=True` réédite même si le
        hash est identique (/refresh)."""
        async with self._lock:
            await self._publish(bot, force=force)

    async def _publish(self, bot, *, force: bool) -> None:
        snap = await self._snapshot(force=force)
        if snap is None:
            return
        state = self.state()
        edited, sent = 0, 0

        for guild_id, _, dest, _ in iter_destinations(bot, self.topic):
            saved = state.get(guild_id)
            message_id = saved.get("message_id")
            if not force and message_id and saved.get("hash") == snap.hash:
                continue  # déjà à jour pour cette version

            new_id, ok = (None, False)
            if message_id:
                new_id, ok = await _edit(dest, message_id, snap, self.tag)
                edited += ok
            if new_id is None:
                # (pas d'id connu, ou message disparu) → message neuf
                new_id = await _send(dest, snap, self.tag)
                ok = new_id is not None
                sent += ok

            if new_id:
                state.set(guild_id, message_id=new_id, content_hash=snap.hash if ok else None)

        if edited or sent:
            await state.save()
            log.info(f"[{self.tag}] {edited} message(s) édité(s), {sent} envoyé(s) (v{snap.post.version}).")

    async def refresh(self, bot) -> None:
        """/refresh : contenu recalculé (données live re-tirées), puis
        ré-édition forcée (sans ping)."""
        await self.state().invalidate()
        await self.publish(bot, force=True)

    async def on_added(self, bot, guild_id, info: dict) -> None:
        """Nouveau salon configuré → publication initiale immédiate."""
        target = config_destination(bot, guild_id, info)
        if target is None:
            return
        snap = await self._snapshot()
        if snap is None:
            return
        new_id = await _send(target[1], snap, self.tag)
        if new_id:
            state = self.state()
            state.set(guild_id, message_id=new_id, content_hash=snap.hash)
            await state.save()
            log.info(f"[{self.tag}] Message publié dans {target[0].name} (nouveau salon).")

    async def on_removed(self, bot, guild_id, info: dict) -> None:
        """Salon retiré → suppression du message + purge de l'état."""
        state = self.state()
        target = config_destination(bot, guild_id, info)
        if target is not None:
            await delete_message(target[1], state.get(guild_id).get("message_id"))
        state.purge(guild_id)
        await state.save()
