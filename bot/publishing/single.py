# -*- coding: utf-8 -*-
"""Publication MONO-message persistante : UN message par abonné, supprimé puis
reposté à chaque actualisation. Le repost (et non l'édition) déclenche une
notification, donc ré-active le ping rôle (injecté DANS la vue)."""
from __future__ import annotations

from typing import Awaitable, Callable

import discord

from bot.publishing.primitives import delete_message, iter_destinations, send_view


async def publish_persistent_view(
    bot: discord.Client,
    topic: str,
    build_view: Callable[[], Awaitable[tuple[discord.ui.LayoutView, list[discord.File]]]],
    content_hash: str,
    state,
    *,
    ping: bool = True,
):
    """Publie/reposte UN message persistant par abonné du topic.

    `build_view()` est une factory asynchrone renvoyant (view, files) NEUFS à
    chaque appel. `content_hash` identifie le contenu : si identique au dernier
    publié (et un message_id est connu), on ne fait rien. Sinon l'ancien message
    est supprimé puis reposté — ce repost (re)déclenche la notification.
    `state` est un WeeklyMessageState.

    `ping` (défaut True) : injecte la mention rôle sur le repost. Un refresh
    manuel (/refresh) passe `ping=False` pour reposter SANS re-notifier —
    exception à la règle « repost = ping »."""
    for guild_id, _, dest, info in iter_destinations(bot, topic):
        saved = state.get(guild_id, topic)
        message_id = saved.get("message_id")
        if message_id and saved.get("hash") == content_hash:
            continue  # contenu inchangé → rien à faire

        await delete_message(dest, message_id)

        view, files = await build_view()
        new_id = await send_view(dest, view, files, role_id=info.get("role"), ping=ping)
        if new_id:
            state.set(guild_id, topic, message_id=new_id, content_hash=content_hash)
            state.save()
