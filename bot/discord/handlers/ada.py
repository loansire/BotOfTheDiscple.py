# -*- coding: utf-8 -*-
"""Handlers de publication Ada-1 (sans @tasks.loop).

Appelés par la pipeline (cogs/pipeline.py) et le routeur /botconfig
(handlers/topics.py) :
- publish        : au reset du MARDI — supprime tout puis republie le(s)
  message(s) de contenu par serveur, suivis d'un message de ping rôle SEUL en
  dernier (si un rôle est défini). `ping=False` (refresh manuel) reposte sans
  notifier.
- restore        : répare les messages disparus (sans ping), au reset.
- on_added       : publie le contenu courant dans un salon nouvellement
  configuré (avec message de ping rôle seul en dernier).
- on_removed     : supprime tous les messages d'un salon retiré + purge l'état.

Ada-1 est un vendor PERMANENT : pas de fenêtre présent/absent, pas de message
statut, pas de largeIcon — juste le(s) message(s) de contenu (normalement 1),
suivi(s) de l'éventuel message de ping.

Ping rôle : c'est un message à part (mention seule, via send_ping), posté en
DERNIER et seulement si un rôle est défini. Son id est rangé avec les messages
de contenu (message_ids) → supprimé/reposté avec eux.

Phase fetch isolée (via _fetch_items) : un fetch indisponible → on ne touche à
rien (le hold mode de la pipeline transforme l'indisponibilité API en attente).

Cache d'images : publish PURGE le cache d'icônes (banners/ada/, cadence HEBDO du
mardi) AVANT régénération, une fois le fetch confirmé. restore / on_added ne
purgent PAS (réutilisation du cache existant) — ainsi un cache frais n'est jamais
effacé juste après composition. La cadence hebdo (purge au seul reset du mardi)
ne touche jamais les caches d'autres features (dossiers séparés)."""
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
from bot.embeds.ada import build_ada_view
from bot.embeds.xur_image import purge_icon_cache
from bot.features.ada import TOPIC, get_ada
from bot.utils.logger import log
from bot.utils.subscriptions import iter_subscribers

_FEATURE = "ada"  # sous-dossier de cache d'icônes (banners/ada/)


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
    """guild_id → (dest_id, is_thread) pour les abonnés du topic Ada-1."""
    return {
        gid: (did, info.get("is_thread", False))
        for gid, did, info in iter_subscribers(TOPIC)
    }


async def _fetch_items():
    """Items Ada-1, ou None si indisponible/vide.

    get_ada renvoie [] à la fois si l'API est indisponible et si le filtre ne
    laisse rien : on traite les deux comme « rien à publier » (on ne poste pas
    un message vide au reset). Une BungieMaintenanceError éventuelle remonte
    (get_ada ne l'attrape pas) → hold mode côté pipeline."""
    items = await get_ada()
    if not items:
        return None
    return items


def _ada_hash(items) -> str:
    """Hash du contenu (inclut l'iso du reset → repost hebdo garanti au mardi)."""
    reset_id = last_reset().isoformat()
    return content_hash([reset_id, *[str(it.item_hash) for it in items]])


async def _repost_guild(
    guild, dest, items, role_id, ada_hash, state, *, ping: bool = True
) -> None:
    """Supprime tout puis republie le(s) message(s) de contenu, suivis d'un
    message de ping rôle SEUL en dernier (si demandé et rôle défini).

    Le ping est un message à part (mention seule) : son id est rangé avec les
    messages de contenu → supprimé/reposté avec eux."""
    guild_id = str(guild.id)
    old = state.get(guild_id)

    # 1) Supprime les anciens messages (contenu + ancien ping).
    await _delete_messages(dest, old["message_ids"])

    # 2) Republie message par message (jamais de ping).
    new_ids: list = []
    views = await build_ada_view(items)
    for view, files in views:
        mid = await send_view(dest, view, files)
        if mid:
            new_ids.append(mid)
    content_count = len(new_ids)

    # 3) Ping rôle SEUL, en dernier (si demandé et rôle défini).
    if ping:
        ping_id = await send_ping(dest, role_id)
        if ping_id:
            new_ids.append(ping_id)

    # 4) Sauvegarde de l'état du serveur.
    state.set(guild_id, message_ids=new_ids, content_hash=ada_hash)
    log.info(f"[Ada-1] {content_count} message(s) publié(s) dans {guild.name}.")


# ── Reset hebdo (mardi) : publication ────────────────────────────────────


async def publish(bot, state, *, ping: bool = True) -> None:
    """Publie/reposte le contenu Ada-1 au reset du mardi.

    Saute un serveur déjà à jour pour ce reset (même hash + messages présents).
    Purge le cache d'icônes (cadence hebdo) AVANT toute régénération, une fois le
    fetch confirmé. `ping=False` (refresh manuel) reposte sans notifier."""
    items = await _fetch_items()
    if items is None:
        log.warning("[Ada-1] Aucun item récupéré — publication annulée.")
        return

    purge_icon_cache(_FEATURE)
    ada_hash = _ada_hash(items)

    for guild_id, dest_id, info in iter_subscribers(TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id)
        if saved["hash"] == ada_hash and saved["message_ids"]:
            continue  # déjà publié pour ce reset

        await _repost_guild(
            guild, dest, items, info.get("role"), ada_hash, state, ping=ping
        )

    state.save()


# ── Réparation des messages disparus (sans ping) ─────────────────────────


async def restore(bot, state) -> None:
    """Répare les messages Ada-1 disparus (sans ping).

    Si un message manque pour un serveur, on reconstruit TOUT ce serveur (plus
    simple et fiable). Fetch paresseux (aucun fetch si rien ne manque). Ne purge
    PAS le cache d'icônes (réparation = réutilisation du cache)."""
    dest_by_guild = _dest_map()
    items = None
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
            items = await _fetch_items()
            fetched = True
        if items is None:
            continue  # fetch impossible → laissé au hold mode

        await _repost_guild(
            guild, dest, items, None, _ada_hash(items), state, ping=False
        )

    state.save()


# ── Hooks /botconfig ─────────────────────────────────────────────────────


async def on_added(bot, state, guild_id, info) -> None:
    """Ajout d'un salon Ada-1. `info` = {channel_id, is_thread, role_id}.
    Publie le contenu courant (+ message de ping seul en dernier). Ne purge PAS
    le cache."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return

    items = await _fetch_items()
    if items is None:
        return

    # Suppression défensive d'anciens messages éventuellement mémorisés.
    await _delete_messages(dest, state.get(guild_id)["message_ids"])
    await _repost_guild(
        guild, dest, items, info.get("role_id"), _ada_hash(items), state, ping=True
    )
    state.save()


async def on_removed(bot, state, guild_id, info) -> None:
    """Retrait d'un salon Ada-1 : supprime les messages, purge l'état."""
    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await _delete_messages(dest, state.get(guild_id)["message_ids"])
    state.purge(guild_id)
    state.save()