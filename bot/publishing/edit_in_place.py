# -*- coding: utf-8 -*-
"""Publication par ÉDITION EN PLACE (un message par serveur, édité à chaque
nouvelle période) — partagée par les Défis ascendants et la Distorsion.

- AUCUN ping (l'édition ne notifie pas) ;
- le message garde sa position dans le salon ;
- idempotent grâce au `content_hash` : un salon déjà à jour est ignoré ;
- rattrapage (période changée pendant une coupure) et réparation (message
  supprimé à la main → renvoi d'un message neuf).

Le hash n'est enregistré QUE si l'édition/l'envoi a réussi : sur une erreur
transitoire (rate-limit, 5xx, permissions), l'id est conservé mais le hash est
vidé, pour que le prochain tick retente au lieu de croire le salon à jour."""
from __future__ import annotations

from typing import Callable

import discord

from bot.publishing.primitives import delete_message, resolve_destination
from bot.core.logger import log
from bot.storage.subscriptions import iter_subscribers

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


async def publish(
    bot, state, topic: str, build: ViewFactory, chash: str, *, force: bool, tag: str
) -> None:
    """Met à jour tous les salons abonnés. `force=True` réédite même si le hash
    est identique (/refresh)."""
    changed = False

    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id)
        message_id = saved.get("message_id")
        if not force and message_id and saved.get("hash") == chash:
            continue  # déjà à jour pour cette période

        new_id, ok = (None, False)
        if message_id:
            new_id, ok = await _edit(dest, message_id, build, tag)
        if new_id is None:
            # (pas d'id connu, ou message disparu) → message neuf
            new_id = await _send(dest, build, tag)
            ok = new_id is not None

        if new_id:
            state.set(guild_id, message_id=new_id, content_hash=chash if ok else None)
            changed = True

    if changed:
        state.save()


async def on_added(
    bot, state, guild_id, dest_info: dict, build: ViewFactory, chash: str, *, tag: str
) -> None:
    """Nouveau salon configuré → publication initiale immédiate."""
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return
    dest = resolve_destination(
        guild, dest_info["channel_id"], dest_info.get("is_thread", False)
    )
    if dest is None:
        return
    new_id = await _send(dest, build, tag)
    if new_id:
        state.set(guild_id, message_id=new_id, content_hash=chash)
        state.save()


async def on_removed(bot, state, guild_id, dest_info: dict) -> None:
    """Salon retiré → suppression du message + purge de l'état."""
    guild = bot.get_guild(int(guild_id))
    message_id = state.get(guild_id).get("message_id")
    if guild is not None and message_id:
        dest = resolve_destination(
            guild, dest_info["channel_id"], dest_info.get("is_thread", False)
        )
        if dest is not None:
            await delete_message(dest, message_id)
    state.purge(guild_id)
    state.save()
