# -*- coding: utf-8 -*-
"""Dispatch d'un embed vers tous les abonnés d'un topic."""
from typing import Callable, Optional

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