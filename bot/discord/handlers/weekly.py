# -*- coding: utf-8 -*-
"""Handlers de publication weekly/daily (sans @tasks.loop).

Appelés par la pipeline (cogs/pipeline.py) et par le routeur /botconfig
(handlers/topics.py) :
- publish_lost_sectors / publish_raid_dungeon : publication au reset (avec ping).
- restore             : répare les messages disparus (sans ping), au reset.
- on_added            : publie le contenu courant dans un salon nouvellement
  configuré (avec ping).
- on_removed          : supprime le message d'un salon retiré + purge l'état.

Le hash de contenu inclut l'identifiant du reset courant (last_reset) : un
repost a donc lieu à chaque cadence (quotidienne pour les secteurs, hebdo pour
raids/donjons) même si les noms d'activités sont identiques d'une période à
l'autre — ce qui garde à jour la ligne « Prochaine actualisation ». Dans une
même période le hash est stable, donc un serveur déjà à jour n'est pas reposté.

Phase fetch isolée en amont : un fetch vide → on ne publie rien (le hold mode
du Lot 4 transformera l'indisponibilité API en attente)."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.discord.publisher import (
    content_hash,
    delete_message,
    message_exists,
    publish_persistent_view,
    resolve_destination,
    send_view,
)
from bot.embeds.weekly import build_lost_sectors_view, build_raid_dungeon_view
from bot.features.weekly import get_lost_sectors, get_raid_dungeon
from bot.utils.subscriptions import iter_subscribers

LOST_SECTOR_TOPIC = "daily_lost_sector"
RAID_DUNGEON_TOPIC = "weekly_raid_dungeon"


# ── Payloads (fetch + hash), partagés par tous les chemins ──────────────


async def _sectors_payload():
    """(sectors, hash) ou None si indisponible."""
    sectors = await get_lost_sectors()
    if not sectors:
        return None
    reset_id = last_reset().isoformat()
    h = content_hash([reset_id, *(str(v.activity_hash) for s in sectors for v in s.variants)])
    return sectors, h


async def _raid_dungeon_payload():
    """(groups, hash) ou None si indisponible."""
    groups = await get_raid_dungeon()
    if not groups:
        return None
    reset_id = last_reset().isoformat()
    h = content_hash([reset_id, *(g.base_name for g in groups if g.featured)])
    return groups, h


_TOPIC_SPECS = {
    LOST_SECTOR_TOPIC: (_sectors_payload, build_lost_sectors_view),
    RAID_DUNGEON_TOPIC: (_raid_dungeon_payload, build_raid_dungeon_view),
}


# ── Publication au reset (avec ping) ────────────────────────────────────


async def publish_lost_sectors(bot, state) -> None:
    """Secteurs oubliés du jour."""
    payload = await _sectors_payload()
    if payload is None:
        return
    sectors, h = payload
    await publish_persistent_view(
        bot,
        LOST_SECTOR_TOPIC,
        build_view=lambda data=sectors: build_lost_sectors_view(data),
        content_hash=h,
        state=state,
    )


async def publish_raid_dungeon(bot, state) -> None:
    """Raids/donjons featured de la semaine."""
    payload = await _raid_dungeon_payload()
    if payload is None:
        return
    groups, h = payload
    await publish_persistent_view(
        bot,
        RAID_DUNGEON_TOPIC,
        build_view=lambda data=groups: build_raid_dungeon_view(data),
        content_hash=h,
        state=state,
    )


# ── Réparation des messages disparus (point 4, sans ping) ───────────────


async def restore(bot, state) -> None:
    """Pour chaque topic weekly : republie SANS ping les messages sauvegardés
    qui n'existent plus sur Discord. Le fetch de contenu est paresseux (aucun
    fetch si rien ne manque)."""
    for topic, (payload_fn, build) in _TOPIC_SPECS.items():
        missing = []
        for guild_id, dest_id, info in iter_subscribers(topic):
            guild = bot.get_guild(int(guild_id))
            if not guild:
                continue
            dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
            if dest is None:
                continue
            mid = state.get(guild_id, topic).get("message_id")
            if not mid:
                continue  # jamais publié → géré au reset / à l'ajout
            if not await message_exists(dest, mid):
                missing.append((guild_id, dest))

        if not missing:
            continue
        payload = await payload_fn()
        if payload is None:
            continue
        data, h = payload
        for guild_id, dest in missing:
            view, files = await build(data)
            new_mid = await send_view(dest, view, files, ping=False)
            if new_mid:
                state.set(guild_id, topic, message_id=new_mid, content_hash=h)
        state.save()


# ── Hooks /botconfig ────────────────────────────────────────────────────


async def on_added(bot, state, guild_id, topic, info) -> None:
    """Publie le contenu courant du topic dans le salon nouvellement configuré
    (avec ping). `info` = {channel_id, is_thread, role_id} (forme config)."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return

    payload_fn, build = _TOPIC_SPECS[topic]
    payload = await payload_fn()
    if payload is None:
        return
    data, h = payload

    # Suppression défensive d'un éventuel ancien message mémorisé pour ce topic.
    await delete_message(dest, state.get(guild_id, topic).get("message_id"))

    view, files = await build(data)
    mid = await send_view(dest, view, files, role_id=info.get("role_id"), ping=True)
    if mid:
        state.set(guild_id, topic, message_id=mid, content_hash=h)
        state.save()


async def on_removed(bot, state, guild_id, topic, info) -> None:
    """Supprime le message du salon retiré et purge l'état du topic."""
    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await delete_message(dest, state.get(guild_id, topic).get("message_id"))
    state.purge(guild_id, topic)
    state.save()