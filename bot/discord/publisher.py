# -*- coding: utf-8 -*-
"""Dispatch vers les abonnés d'un topic.

Deux régimes de publication :
- publish_to_subscribers : événementiel — un nouveau message par événement
  (news, maintenance). Conserve l'historique.
- publish_persistent_view : persistant — UN message par abonné, supprimé puis
  reposté à chaque actualisation. Le repost (et non l'édition) permet de
  déclencher une notification et donc de ré-activer le ping rôle.

Helpers partagés (utilisés aussi par les handlers de la pipeline) :
- content_hash()       : hash court et stable d'un itérable de chaînes.
- resolve_destination(): résout un salon texte ou un thread cible.
- send_view()          : envoie une LayoutView (+ ping rôle optionnel) → id|None.
- send_ping()          : envoie un message de mention rôle SEUL (hors CV2) → id|None.
- message_exists()     : True si le message existe encore (NotFound → False).
- delete_message()     : supprime un message (ignore s'il a déjà disparu).
"""
import hashlib
from typing import Awaitable, Callable, Optional

import discord
from discord import ui

from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers


def content_hash(parts) -> str:
    """Hash court et stable d'un itérable de chaînes (ordre indépendant)."""
    joined = "|".join(sorted(parts))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def resolve_destination(
    guild: discord.Guild, dest_id: str, is_thread: bool
) -> Optional[discord.abc.Messageable]:
    """Salon texte ou thread cible, ou None si introuvable/incompatible."""
    if is_thread:
        th = guild.get_thread(int(dest_id))
        return th if isinstance(th, discord.Thread) else None
    ch = guild.get_channel(int(dest_id))
    return ch if isinstance(ch, discord.TextChannel) else None


async def send_view(
    dest,
    view: discord.ui.LayoutView,
    files: Optional[list] = None,
    *,
    role_id: Optional[str] = None,
    ping: bool = False,
) -> Optional[str]:
    """Envoie une LayoutView. Injecte le ping rôle si `ping` et `role_id`.

    Components V2 : un LayoutView ne peut pas porter de `content` ; la mention
    est ajoutée comme TextDisplay, et `allowed_mentions` n'autorise QUE le rôle
    voulu. Renvoie l'id (str) du message envoyé, ou None en cas d'échec.

    NB : pour un ping « en dernier sur un message à part » (cas des vendors),
    préférer send_ping() plutôt que ce paramètre `ping`."""
    if ping and role_id:
        view.add_item(ui.TextDisplay(f"<@&{role_id}>"))
        allowed = discord.AllowedMentions(roles=True)
    else:
        allowed = discord.AllowedMentions.none()
    try:
        sent = await dest.send(view=view, files=files or [], allowed_mentions=allowed)
        return str(sent.id)
    except discord.DiscordException as e:
        log.error(f"[Publisher] Envoi échoué dans {dest} : {e}")
        return None


async def send_ping(dest, role_id: Optional[str]) -> Optional[str]:
    """Envoie un message de ping rôle SEUL (contenu = mention, hors CV2).

    C'est un message texte classique (PAS une LayoutView) : la mention vit donc
    dans le champ `content`, ce qui déclenche la notification de façon fiable et
    standard — contrairement à un `<@&…>` glissé dans un TextDisplay d'un message
    Components V2.

    Renvoie l'id (str) du message envoyé, ou None si aucun rôle n'est défini
    (rien n'est alors publié) ou en cas d'échec d'envoi."""
    if not role_id:
        return None
    try:
        sent = await dest.send(
            content=f"<@&{role_id}>",
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        return str(sent.id)
    except discord.DiscordException as e:
        log.error(f"[Publisher] Envoi du ping échoué dans {dest} : {e}")
        return None


async def message_exists(dest, message_id) -> bool:
    """True si le message existe encore. NotFound → False. Erreur transitoire
    → True (on ne reposte pas, pour éviter un doublon en cas de rate-limit)."""
    if not message_id:
        return False
    try:
        await dest.fetch_message(int(message_id))
        return True
    except discord.NotFound:
        return False
    except discord.DiscordException:
        return True


async def delete_message(dest, message_id) -> None:
    """Supprime un message (ignore s'il a déjà disparu)."""
    if not message_id:
        return
    try:
        msg = await dest.fetch_message(int(message_id))
        await msg.delete()
    except discord.NotFound:
        pass
    except discord.DiscordException as e:
        log.warning(f"[Publisher] Suppression échouée : {e}")


async def publish_to_subscribers(bot: discord.Client, topic: str, build: Callable):
    """`build()` doit renvoyer (embed, files, view) NEUFS à chaque appel
    (un discord.File est consommé après envoi)."""
    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
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
    publié (et un message_id est connu), on ne fait rien. Sinon l'ancien message
    est supprimé puis reposté (avec ping rôle) — ce repost (re)déclenche la
    notification. `state` est un WeeklyMessageState."""
    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id, topic)
        message_id = saved.get("message_id")
        if message_id and saved.get("hash") == content_hash:
            continue  # contenu inchangé → rien à faire

        await delete_message(dest, message_id)

        view, files = await build_view()
        new_id = await send_view(dest, view, files, role_id=info.get("role"), ping=True)
        if new_id:
            state.set(guild_id, topic, message_id=new_id, content_hash=content_hash)
            state.save()