# -*- coding: utf-8 -*-
"""Dispatch vers les abonnés d'un topic.

Deux régimes de publication :
- publish_to_subscribers : événementiel — un nouveau message par événement
  (news, maintenance). Conserve l'historique.
- publish_persistent_view : persistant — UN message par abonné, supprimé puis
  reposté à chaque actualisation. Le repost (et non l'édition) permet de
  déclencher une notification et donc de ré-activer le ping rôle.
"""
from typing import Awaitable, Callable, Optional

import discord
from discord import ui

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
    """Publie/reposte UN message persistant par abonné du topic.

    `build_view()` est une factory asynchrone renvoyant (view, files) NEUFS à
    chaque appel. `content_hash` identifie le contenu : si identique au dernier
    publié, on ne fait rien. `state` est un WeeklyMessageState.

    Comportement : si un message précédent existe, il est SUPPRIMÉ avant le
    repost — c'est ce repost qui (re)déclenche la notification et le ping rôle.

    Ping rôle (Components V2) : un message LayoutView ne peut pas porter de
    `content` (rejeté par l'API Discord). La mention est donc ajoutée comme
    `TextDisplay` dans la vue, et `allowed_mentions` n'autorise QUE la mention
    de rôle voulue (aucun ping parasite si aucun rôle n'est configuré)."""
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
            continue  # contenu inchangé → rien à faire

        # 1) Suppression de l'ancien message (s'il existe encore)
        if message_id:
            try:
                old_msg = await dest.fetch_message(int(message_id))
                await old_msg.delete()
            except discord.NotFound:
                pass  # déjà supprimé → on reposte simplement
            except discord.DiscordException as e:
                log.warning(
                    f"[Publisher] Suppression ancien message échouée ({topic}) : {e}"
                )

        # 2) Construction de la vue neuve + injection éventuelle du ping rôle
        view, files = await build_view()
        role_id = info.get("role")
        if role_id:
            view.add_item(ui.TextDisplay(f"<@&{role_id}>"))
            allowed = discord.AllowedMentions(roles=True)
        else:
            allowed = discord.AllowedMentions.none()

        # 3) Repost et mémorisation du nouvel état
        try:
            sent = await dest.send(view=view, files=files, allowed_mentions=allowed)
            state.set(guild_id, topic, message_id=str(sent.id), content_hash=content_hash)
            state.save()
        except discord.DiscordException as e:
            log.error(f"[Publisher] Message persistant échoué dans {dest} ({topic}) : {e}")