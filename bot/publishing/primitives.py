# -*- coding: utf-8 -*-
"""Briques Discord bas niveau partagées par tous les moteurs de publication.

- content_hash()        : hash court et stable d'un itérable de chaînes.
- resolve_destination() : résout un salon texte ou un thread cible.
- iter_destinations()   : abonnés JOIGNABLES d'un topic (guild + salon résolus).
- config_destination()  : idem pour une destination au format /botconfig.
- send_view()           : envoie une LayoutView (+ ping rôle optionnel) → id|None.
- send_ping()           : envoie un message de mention rôle SEUL (hors CV2) → id|None.
- message_exists()      : True si le message existe encore (NotFound → False).
- all_exist()           : idem pour une liste (vérifications en parallèle).
- delete_message(s)()   : supprime un/des message(s) (ignore ceux déjà disparus).
- destinations_by_guild(): guild_id → (guild, dest) des abonnés joignables.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Iterator, Optional

import discord
from discord import ui

from bot.core.logger import log
from bot.storage.subscriptions import iter_subscribers


def content_hash(parts) -> str:
    """Hash court et stable d'un itérable de chaînes (ordre indépendant)."""
    joined = "|".join(sorted(parts))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


# ── Destinations ────────────────────────────────────────────────────────


def resolve_destination(
    guild: discord.Guild, dest_id: str, is_thread: bool
) -> Optional[discord.abc.Messageable]:
    """Salon texte ou thread cible, ou None si introuvable/incompatible."""
    if is_thread:
        th = guild.get_thread(int(dest_id))
        return th if isinstance(th, discord.Thread) else None
    ch = guild.get_channel(int(dest_id))
    return ch if isinstance(ch, discord.TextChannel) else None


def iter_destinations(
    bot: discord.Client, topic: str
) -> Iterator[tuple[str, discord.Guild, discord.abc.Messageable, dict]]:
    """Abonnés joignables d'un topic : (guild_id, guild, dest, info).

    `info` = {name, is_thread, role} (forme subscriptions.json). Les serveurs
    quittés et les salons supprimés/incompatibles sont ignorés."""
    for guild_id, dest_id, info in iter_subscribers(topic):
        guild = bot.get_guild(int(guild_id))
        if guild is None:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue
        yield guild_id, guild, dest, info


def destinations_by_guild(
    bot: discord.Client, topic: str
) -> dict[str, tuple[discord.Guild, discord.abc.Messageable]]:
    """guild_id → (guild, dest) des abonnés joignables d'un topic. Sert aux
    boucles qui parcourent un ÉTAT (serveurs déjà publiés) plutôt que les
    abonnements."""
    return {gid: (guild, dest) for gid, guild, dest, _ in iter_destinations(bot, topic)}


def config_destination(
    bot: discord.Client, guild_id, info: dict
) -> Optional[tuple[discord.Guild, discord.abc.Messageable]]:
    """(guild, dest) d'une destination au format /botconfig
    ({channel_id, is_thread, role_id}), ou None si injoignable."""
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return None
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return None
    return guild, dest


# ── Envoi ───────────────────────────────────────────────────────────────


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


# ── Existence / suppression ─────────────────────────────────────────────


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


async def all_exist(dest, ids) -> bool:
    """True si tous les messages de la liste existent encore (liste vide →
    True). Les vérifications partent en parallèle ; en cas de rate-limit,
    discord.py met lui-même les requêtes en attente."""
    results = await asyncio.gather(*(message_exists(dest, mid) for mid in ids))
    return all(results)


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


async def delete_messages(dest, ids) -> None:
    """Supprime une liste de messages, dans l'ordre (ignore ceux déjà absents)."""
    for mid in ids:
        await delete_message(dest, mid)
