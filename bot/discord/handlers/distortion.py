# -*- coding: utf-8 -*-
"""Handler de publication de la Distorsion.

Spécificité vs les autres features : mise à jour par ÉDITION EN PLACE (le
message avance d'un cran chaque heure), donc :
- AUCUN ping (l'édition ne notifie pas ; le topic n'expose d'ailleurs pas de
  rôle configurable) ;
- le message garde sa position dans le salon (pas de repost horaire).

`publish` est idempotent grâce au `content_hash` : un salon déjà à jour est
ignoré. Il couvre aussi le rattrapage (heure changée pendant une coupure) et la
réparation (message supprimé à la main → renvoi)."""
from __future__ import annotations

from datetime import datetime, timezone

import discord

from bot.discord.publisher import delete_message, resolve_destination
from bot.embeds.distortion import build_distortion_view, content_hash
from bot.features.distortion import TOPIC
from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers


async def _send(dest, view, files) -> str | None:
    """Envoie un message neuf (Components V2, sans contenu → aucun ping)."""
    try:
        sent = await dest.send(view=view, files=files)
        return str(sent.id)
    except discord.DiscordException as e:
        log.error(f"[Distortion] Envoi échoué dans {dest} : {e}")
        return None


async def _edit(dest, message_id: str, view, files) -> str | None:
    """Édite le message existant. Renvoie l'id conservé, ou None si le message
    a disparu (→ le caller renverra un message neuf)."""
    try:
        msg = await dest.fetch_message(int(message_id))
        await msg.edit(attachments=files, view=view)
        return message_id
    except discord.NotFound:
        return None  # supprimé à la main → renvoi par le caller
    except discord.DiscordException as e:
        log.warning(f"[Distortion] Édition échouée ({message_id}) : {e}")
        return message_id  # on garde l'id, nouvelle tentative au prochain tick


async def publish(bot, state, *, force: bool = False) -> None:
    """Met à jour tous les salons abonnés à l'heure courante.

    `force=True` (utilisé par /refresh) rééédite même si le hash est identique."""
    now = datetime.now(timezone.utc)
    chash = content_hash(now)
    changed = False

    for guild_id, dest_id, info in iter_subscribers(TOPIC):
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id)
        message_id = saved.get("message_id")
        if not force and message_id and saved.get("hash") == chash:
            continue  # déjà à jour pour cette heure

        view, files = build_distortion_view(now)
        new_id = None
        if message_id:
            new_id = await _edit(dest, message_id, view, files)
        if new_id is None:
            # (pas d'id connu, ou message disparu) → nouvelle vue neuve
            view, files = build_distortion_view(now)
            new_id = await _send(dest, view, files)

        if new_id:
            state.set(guild_id, message_id=new_id, content_hash=chash)
            changed = True

    if changed:
        state.save()


async def refresh(bot, state) -> None:
    """Réactualisation forcée (sans ping) pour /refresh."""
    state.invalidate()
    await publish(bot, state, force=True)


async def on_added(bot, state, guild_id, dest_info: dict) -> None:
    """Nouveau salon configuré → publication initiale immédiate."""
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return
    dest = resolve_destination(
        guild, dest_info["channel_id"], dest_info.get("is_thread", False)
    )
    if dest is None:
        return
    now = datetime.now(timezone.utc)
    view, files = build_distortion_view(now)
    new_id = await _send(dest, view, files)
    if new_id:
        state.set(guild_id, message_id=new_id, content_hash=content_hash(now))
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
