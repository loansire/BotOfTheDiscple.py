# -*- coding: utf-8 -*-
"""Handlers de publication Eververse (sans @tasks.loop).

Appelés par la pipeline (cogs/pipeline.py) et le routeur /botconfig
(handlers/topics.py) :
- publish        : au reset QUOTIDIEN — supprime tout puis republie les 3
  messages de sections par serveur, suivis d'un message de ping rôle SEUL en
  dernier (si un rôle est défini).
- restore        : répare les messages disparus (sans ping), au reset.
- on_added       : publie le contenu courant dans un salon nouvellement
  configuré (avec message de ping rôle seul en dernier).
- on_removed     : supprime tous les messages d'un salon retiré + purge l'état.

Contrairement à Xûr : pas de fenêtre présent/absent, pas de message « statut »,
pas de largeIcon — juste les 3 messages de sections (+ éventuel ping en dernier).

Ping rôle : c'est un message à part (mention seule, via send_ping), posté en
DERNIER et seulement si un rôle est défini. Son id est rangé avec les messages
de sections (message_ids) → supprimé/reposté avec eux.

Phase fetch isolée (via _fetch_sections) : un fetch indisponible → on ne touche
à rien (le hold mode de la pipeline transforme l'indisponibilité API en attente).

Cache d'images : publish PURGE le cache d'icônes (banners/eververse/, cadence
quotidienne) AVANT régénération, une fois le fetch confirmé. restore / on_added
ne purgent PAS (réutilisation du cache existant) — ainsi un cache frais n'est
jamais effacé juste après composition."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.discord.publisher import (
    content_hash,
    delete_message,
    message_exists,
    resolve_destination,
    send_ping,
    send_view,
)
from bot.embeds.eververse import build_eververse_views
from bot.embeds.xur_image import purge_icon_cache
from bot.features.eververse import TOPIC, get_eververse
from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers

_FEATURE = "eververse"  # sous-dossier de cache d'icônes (banners/eververse/)


# ── Helpers ─────────────────────────────────────────────────────────────


async def _delete_messages(dest, ids) -> None:
    """Supprime une liste de messages (ignore ceux déjà absents)."""
    for mid in ids:
        await delete_message(dest, mid)


async def _all_exist(dest, ids) -> bool:
    """True si tous les messages de la liste existent encore."""
    for mid in ids:
        if not await message_exists(dest, mid):
            return False
    return True


def _dest_map() -> dict:
    """guild_id → (dest_id, is_thread) pour les abonnés du topic Eververse."""
    return {
        gid: (did, info.get("is_thread", False))
        for gid, did, info in iter_subscribers(TOPIC)
    }


async def _fetch_sections():
    """Les 3 sections Eververse, ou None si l'API est indisponible.

    Une section sans item est conservée (le rendu affiche un repli) : seul un
    échec API total (get_eververse renvoie []) est traité comme indisponible."""
    sections = await get_eververse()
    if not sections:
        return None
    return sections


def _eververse_hash(sections) -> str:
    """Hash du contenu (inclut l'iso du reset → repost quotidien garanti)."""
    reset_id = last_reset().isoformat()
    parts = [reset_id]
    for section in sections:
        for item in section.items:
            parts.append(str(item.item_hash))
    return content_hash(parts)


async def _repost_guild(
    guild, dest, sections, role_id, ev_hash, state, *, ping: bool = True
) -> None:
    """Supprime tout puis republie les 3 messages de sections, suivis d'un
    message de ping rôle SEUL en dernier (si demandé et rôle défini).

    Le ping est un message à part (mention seule) : son id est rangé avec les
    messages de sections → supprimé/reposté avec eux."""
    guild_id = str(guild.id)
    old = state.get(guild_id)

    # 1) Supprime les anciens messages (sections + ancien ping).
    await _delete_messages(dest, old["message_ids"])

    # 2) Republie section par section (jamais de ping).
    new_ids: list = []
    views = await build_eververse_views(sections)
    for view, files in views:
        mid = await send_view(dest, view, files)
        if mid:
            new_ids.append(mid)
    section_count = len(new_ids)

    # 3) Ping rôle SEUL, en dernier (si demandé et rôle défini).
    if ping:
        ping_id = await send_ping(dest, role_id)
        if ping_id:
            new_ids.append(ping_id)

    # 4) Sauvegarde de l'état du serveur.
    state.set(guild_id, message_ids=new_ids, content_hash=ev_hash)
    log.info(f"[Eververse] {section_count} message(s) publié(s) dans {guild.name}.")


# ── Reset quotidien : publication ────────────────────────────────────────


async def publish(bot, state) -> None:
    """Publie/reposte les 3 messages Eververse au reset quotidien.

    Saute un serveur déjà à jour pour ce reset (même hash + messages présents).
    Purge le cache d'icônes (cadence quotidienne) AVANT toute régénération, une
    fois le fetch confirmé."""
    sections = await _fetch_sections()
    if sections is None:
        log.warning("[Eververse] Aucun item récupéré — publication annulée.")
        return

    purge_icon_cache(_FEATURE)
    ev_hash = _eververse_hash(sections)

    for guild_id, dest_id, info in iter_subscribers(TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id)
        if saved["hash"] == ev_hash and saved["message_ids"]:
            continue  # déjà publié pour ce reset

        await _repost_guild(
            guild, dest, sections, info.get("role"), ev_hash, state, ping=True
        )

    state.save()


# ── Réparation des messages disparus (sans ping) ─────────────────────────


async def restore(bot, state) -> None:
    """Répare les messages Eververse disparus (sans ping).

    Si un message manque pour un serveur, on reconstruit TOUT ce serveur (plus
    simple et fiable). Fetch vendor paresseux (aucun fetch si rien ne manque).
    Ne purge PAS le cache d'icônes (réparation = réutilisation du cache)."""
    dest_by_guild = _dest_map()
    sections = None
    fetched = False

    for guild_id, entry in state.iter_guilds():
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest_info = dest_by_guild.get(guild_id)
        if not dest_info:
            continue
        dest = resolve_destination(guild, dest_info[0], dest_info[1])
        if dest is None:
            continue

        ids = entry["message_ids"]
        if ids and await _all_exist(dest, ids):
            continue  # tout est en place

        if not fetched:
            sections = await _fetch_sections()
            fetched = True
        if sections is None:
            continue  # fetch impossible → laissé au hold mode

        await _repost_guild(
            guild, dest, sections, None, _eververse_hash(sections), state, ping=False
        )

    state.save()


# ── Hooks /botconfig ─────────────────────────────────────────────────────


async def on_added(bot, state, guild_id, info) -> None:
    """Ajout d'un salon Eververse. `info` = {channel_id, is_thread, role_id}.
    Publie le contenu courant (+ message de ping seul en dernier). Ne purge PAS
    le cache."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return

    sections = await _fetch_sections()
    if sections is None:
        return

    # Suppression défensive d'anciens messages éventuellement mémorisés.
    await _delete_messages(dest, state.get(guild_id)["message_ids"])
    await _repost_guild(
        guild, dest, sections, info.get("role_id"), _eververse_hash(sections),
        state, ping=True,
    )
    state.save()


async def on_removed(bot, state, guild_id, info) -> None:
    """Retrait d'un salon Eververse : supprime les messages, purge l'état."""
    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await _delete_messages(dest, state.get(guild_id)["message_ids"])
    state.purge(guild_id)
    state.save()