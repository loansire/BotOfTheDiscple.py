# -*- coding: utf-8 -*-
"""Dispatch vers les abonnés d'un topic.

Deux régimes de publication :
- publish_to_subscribers : événementiel — un nouveau message par événement
  (news, maintenance). Conserve l'historique.
- publish_persistent_view : persistant — UN message édité en place
  (weekly/daily). Pas de re-ping (le rôle éventuel est ignoré).
"""
from typing import Awaitable, Callable, Optional

import discord

from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers


def _resolve_destination(
    guild: discord.Guild, dest_id: str, is_thread: bool
) -> Optional[discord.abc.Messageable]:
    if is_thread:
        th = guild.get_thread(int(dest_id))
        return th if isinstance(th, discord.Thread) else None
    ch = guild.get_channel(int(dest_id))
    return ch if isinstance(ch, discord.TextChannel) else None


async def publish_to_subscribers(bot: discord.Client, topic: str, build: Callable):
    """`build()` doit renvoyer (embed, files, view) NEUFS à chaque appel
    (un discord.File est consommé après envoi)."""
    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = _resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        role_id = info.get("role")
        mention = f"<@&{role_id}>" if role_id else None
        embed, files, view = build()
        try:
            if view:
                await dest.send(content=mention, embed=embed, files=files, view=view)
            else:
                await dest.send(content=mention, embed=embed, files=files)
        except discord.DiscordException as e:
            log.error(f"[Publisher] Envoi échoué dans {dest} ({topic}) : {e}")


async def publish_persistent_view(
    bot: discord.Client,
    topic: str,
    build_view: Callable[[], Awaitable[tuple[discord.ui.LayoutView, list[discord.File]]]],
    content_hash: str,
    state,
):
    """Publie/édite UN message persistant par abonné du topic.

    `build_view()` est une factory asynchrone renvoyant (view, files) NEUFS à
    chaque appel. `content_hash` identifie le contenu : si identique au dernier
    publié, on n'édite pas. `state` est un WeeklyMessageState.

    Message Components V2 : à l'édition, on remet explicitement content/embeds
    à vide et on ré-attache les fichiers (contrainte discord.py)."""
    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = _resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id, topic)
        message_id = saved.get("message_id")
        if message_id and saved.get("hash") == content_hash:
            continue  # contenu inchangé → rien à éditer

        view, files = await build_view()
        try:
            if message_id:
                try:
                    msg = await dest.fetch_message(int(message_id))
                    await msg.edit(
                        view=view, attachments=files, content=None, embeds=[]
                    )
                    state.set(guild_id, topic, message_id=message_id, content_hash=content_hash)
                    state.save()
                    continue
                except discord.NotFound:
                    pass  # message supprimé entre-temps → on reposte

            sent = await dest.send(view=view, files=files)
            state.set(guild_id, topic, message_id=str(sent.id), content_hash=content_hash)
            state.save()
        except discord.DiscordException as e:
            log.error(f"[Publisher] Message persistant échoué dans {dest} ({topic}) : {e}")