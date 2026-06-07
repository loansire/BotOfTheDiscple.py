# -*- coding: utf-8 -*-
"""Dispatch d'un embed vers tous les abonnés d'un topic."""
from typing import Callable

import discord

from bot.utils.logger import log
from bot.utils.subscriptions import load_subscriptions


def _resolve_destinations(guild: discord.Guild, conf: dict) -> list:
    dests = []
    channels = conf.get("channels", {})
    cid = channels.get("channel_ID")
    if cid:
        ch = guild.get_channel(int(cid))
        if isinstance(ch, discord.TextChannel):
            dests.append(ch)
    tid = channels.get("thread_ID")
    if tid:
        th = guild.get_thread(int(tid))
        if isinstance(th, discord.Thread):
            dests.append(th)
    return dests


async def publish_to_subscribers(bot: discord.Client, topic: str, build: Callable):
    """`build()` doit renvoyer (embed, files, view) NEUFS à chaque appel
    (un discord.File est consommé après envoi)."""
    subs = load_subscriptions(topic)
    for guild_id, conf in subs.items():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        role_id = conf.get("roles")
        mention = f"<@&{role_id}>" if role_id else None
        for dest in _resolve_destinations(guild, conf):
            embed, files, view = build()
            try:
                if view:
                    await dest.send(content=mention, embed=embed, files=files, view=view)
                else:
                    await dest.send(content=mention, embed=embed, files=files)
            except discord.DiscordException as e:
                log.error(f"[Publisher] Envoi échoué dans {dest} ({topic}) : {e}")