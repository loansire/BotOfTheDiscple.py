# -*- coding: utf-8 -*-
"""Handlers de publication Avant-garde (activités du Portail en focus du jour).

Appelés par la pipeline (cogs/pipeline.py) et par le routeur /botconfig
(bot/publishing/router.py).

Régime MULTI-message, calqué sur les secteurs oubliés : un message par
catégorie (Escouade, Prestige, Arène, Solo), puis le ping rôle SEUL en
dernier. L'état vit dans WeeklyMessageState (set_ids / message_ids), sous le
topic `daily_vanguard`.

Le hash de contenu inclut le reset courant (last_reset) : repost quotidien,
mais un serveur déjà à jour dans la même journée n'est pas reposté.

Garde-fou « données pas prêtes » (`strict=True`, pipeline au reset) : même
logique que features/weekly/handler.py — BungieNotReadyError (hold mode) si aucune
activité n'est détectée ou si le contenu est identique à celui de la veille,
jusqu'à STALE_GRACE après le reset."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.bungie.client import bungie
from bot.bungie.errors import BungieNotReadyError
from bot.bungie.reset import TUESDAY, last_reset, last_weekday_reset
from bot.publishing.primitives import (
    content_hash,
    delete_message,
    message_exists,
    resolve_destination,
    send_ping,
    send_view,
)
from bot.render.banner import purge_banner_cache
from bot.features.vanguard.view import FEATURE, build_vanguard_views
from bot.features.vanguard import TOPIC, get_portal
from bot.features.vanguard.filters import challenges_of
from bot.core.logger import log
from bot.storage.subscriptions import iter_subscribers

# Délai après le reset au-delà duquel un contenu « suspect » est publié quand même.
STALE_GRACE = timedelta(hours=2)


# ── Garde-fou « données pas prêtes » ────────────────────────────────────


def _not_ready(reason: str) -> None:
    if datetime.now(timezone.utc) - last_reset() >= STALE_GRACE:
        log.warning(f"[Avant-garde] {reason} — délai de grâce écoulé, publication quand même.")
        return
    bungie.invalidate_character_cache()
    raise BungieNotReadyError(f"{TOPIC} : {reason}")


def _check_fresh(state, sig: list[str]) -> None:
    """Refuse un contenu identique à celui de la période PRÉCÉDENTE."""
    prev = state.last_signature(TOPIC)
    if not prev or prev.get("period") == last_reset().isoformat():
        return
    if prev.get("sig") == sorted(sig):
        _not_ready("contenu identique à la veille (données périmées ?)")


# ── Payload (fetch + hash) ──────────────────────────────────────────────


async def _payload(state, *, strict: bool = False):
    """(catégories, hash, signature) ou None si rien n'est détecté.

    Les défis (hebdomadaires) vus une fois dans la semaine sont mémorisés dans
    l'état et réaffichés aux resets quotidiens suivants, même une fois
    accomplis sur le personnage de référence (le profil ne les montre plus)."""
    week = last_weekday_reset(TUESDAY).isoformat()
    remembered = state.week_challenges(week)
    categories = await get_portal(remembered)
    seen = challenges_of(categories)
    if categories and seen != remembered:
        state.set_week_challenges(week, {**remembered, **seen})
        state.save()
    sig = [
        f"{a.base_name}|{a.focus_hash}"
        for c in categories for a in c.activities
    ]
    if not sig:
        if strict:
            _not_ready("aucune activité en focus détectée")
        return None
    if strict:
        _check_fresh(state, sig)
    h = content_hash([last_reset().isoformat(), TOPIC, *sig])
    return categories, h, sig


# ── Publication ─────────────────────────────────────────────────────────


async def _delete_all(dest, ids) -> None:
    for mid in ids:
        await delete_message(dest, mid)


async def _repost_guild(guild, dest, categories, role_id, h, state, *, ping: bool) -> None:
    """Supprime les anciens messages (+ ancien ping) puis republie un message
    par catégorie, suivi du ping rôle SEUL en dernier (si demandé)."""
    guild_id = str(guild.id)
    await _delete_all(dest, state.get(guild_id, TOPIC).get("message_ids", []))

    new_ids: list = []
    views = await build_vanguard_views(categories)
    for view, files in views:
        mid = await send_view(dest, view, files)
        if mid:
            new_ids.append(mid)
    sent = len(new_ids)
    # Envoi partiel → hash vide : le serveur sera retenté au prochain publish.
    if sent < len(views):
        log.warning(f"[Avant-garde] {sent}/{len(views)} message(s) envoyé(s) dans {guild.name}.")
        h = ""

    if ping:
        ping_id = await send_ping(dest, role_id)
        if ping_id:
            new_ids.append(ping_id)

    state.set_ids(guild_id, TOPIC, message_ids=new_ids, content_hash=h)
    log.info(f"[Avant-garde] {sent} message(s) publié(s) dans {guild.name}.")


async def publish(bot, state, *, ping: bool = True, strict: bool = False) -> None:
    """Activités du Portail du jour. Purge le cache de bandeaux (cadence
    quotidienne) une fois le fetch confirmé. Saute un serveur déjà à jour."""
    payload = await _payload(state, strict=strict)
    if payload is None:
        return
    categories, h, sig = payload
    purge_banner_cache(FEATURE)

    for guild_id, dest_id, info in iter_subscribers(TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue
        saved = state.get(guild_id, TOPIC)
        if saved.get("hash") == h and saved.get("message_ids"):
            continue  # déjà publié pour ce reset
        await _repost_guild(guild, dest, categories, info.get("role"), h, state, ping=ping)

    state.set_signature(TOPIC, last_reset().isoformat(), sig)
    state.save()


async def restore(bot, state) -> None:
    """Répare les messages disparus (sans ping) : si un message d'un serveur
    manque, tout le serveur est reconstruit. Fetch paresseux."""
    payload = None
    fetched = False

    for guild_id, dest_id, info in iter_subscribers(TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue
        ids = state.get(guild_id, TOPIC).get("message_ids", [])
        if not ids:
            continue  # jamais publié → géré au reset / à l'ajout
        if all([await message_exists(dest, mid) for mid in ids]):
            continue

        if not fetched:
            payload = await _payload(state)
            fetched = True
        if payload is None:
            continue
        categories, h, _ = payload
        await _repost_guild(guild, dest, categories, None, h, state, ping=False)

    state.save()


# ── Hooks /botconfig ────────────────────────────────────────────────────


async def on_added(bot, state, guild_id, info) -> None:
    """Publie dans un salon nouvellement configuré (avec ping)."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return
    payload = await _payload(state)
    if payload is None:
        return
    categories, h, _ = payload
    await _repost_guild(guild, dest, categories, info.get("role_id"), h, state, ping=True)
    state.save()


async def on_removed(bot, state, guild_id, info) -> None:
    """Supprime les messages d'un salon retiré + purge l'état."""
    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await _delete_all(dest, state.get(guild_id, TOPIC).get("message_ids", []))
    state.purge(guild_id, TOPIC)
    state.save()
