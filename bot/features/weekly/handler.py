# -*- coding: utf-8 -*-
"""Handlers de publication weekly/daily (sans @tasks.loop).

Appelés par la pipeline (cogs/pipeline.py) et par le routeur /botconfig
(bot/publishing/router.py).

Deux régimes de message coexistent :
- Raids / Donjons  : MONO-message persistant (via publish_persistent_view,
  état WeeklyMessageState.set / message_id). Jamais près du plafond de 4000
  caractères de texte CV2.
- Secteurs oubliés : MULTI-message (1 message par secteur) — le texte cumulé
  d'un message unique dépassait la limite Discord de 4000 caractères une fois
  les icônes de modificateurs ajoutées. Chaque secteur a son propre message
  (état WeeklyMessageState.set_ids / message_ids), et le ping rôle est un
  message SÉPARÉ posté EN DERNIER (comme Xûr/Eververse/Ada). Son id est rangé
  avec les message_ids → supprimé/reposté avec eux.

`ping` (défaut True) : le reset automatique notifie (repost = ping) ; un refresh
manuel passe `ping=False` — exception assumée à la règle « repost = ping ». Pour
les secteurs, `ping` n'agit que sur le message de mention final.

Le hash de contenu inclut l'identifiant du reset courant (last_reset) : un
repost a donc lieu à chaque cadence (quotidienne pour les secteurs, hebdo pour
raids/donjons) même si les noms d'activités sont identiques d'une période à
l'autre — ce qui garde à jour la ligne « Prochaine actualisation ». Dans une
même période le hash est stable, donc un serveur déjà à jour n'est pas reposté.

Cache d'images : la publication au reset PURGE d'abord le cache de bandeaux de
la feature concernée (à sa cadence : quotidienne pour les secteurs, hebdo pour
raids/donjons), puis régénère. Raids et donjons PARTAGENT le dossier de cache
`raid_donjon` : la purge est faite une seule fois par publish_raid_dungeon AVANT
de publier les deux types. `restore` et `on_added` ne purgent PAS.

Garde-fou « données pas prêtes » (`strict=True`, passé par la pipeline au
reset) : juste après un reset, Bungie sert parfois encore les données de la
période précédente, ou des raids/donjons sans challenges actifs. Publier à ce
moment figerait un contenu faux (avec ping) pour toute la période. On lève donc
BungieNotReadyError (→ hold mode, nouvelle tentative) quand :
- aucun raid / donjon / secteur n'est détecté ;
- le contenu est identique à celui de la période précédente.
Passé STALE_GRACE après le reset, on publie quand même (avec un warning) :
une vraie répétition d'une période à l'autre reste possible."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.bungie.client import bungie
from bot.bungie.errors import BungieNotReadyError
from bot.bungie.reset import TUESDAY, last_reset, last_weekday_reset
from bot.publishing.primitives import (
    content_hash,
    delete_message,
    message_exists,
    publish_persistent_view,
    resolve_destination,
    send_ping,
    send_view,
)
from bot.render.banner import purge_banner_cache
from bot.features.weekly.view import (
    build_dungeon_view,
    build_lost_sectors_view,
    build_raid_view,
)
from bot.features.weekly import get_lost_sectors, get_raid_dungeon
from bot.core.logger import log
from bot.storage.subscriptions import iter_subscribers

LOST_SECTOR_TOPIC = "daily_lost_sector"
RAID_TOPIC = "weekly_raid"
DUNGEON_TOPIC = "weekly_dungeon"

# Délai après le reset au-delà duquel un contenu « suspect » est publié quand même.
STALE_GRACE = timedelta(hours=2)

# Clés de feature pour la purge du cache d'images (cf. render/banner.py).
_FEATURE_LOST_SECTOR = "secteur_oublie"
_FEATURE_RAID_DUNGEON = "raid_donjon"  # partagé raids + donjons


# ── Helpers messages ────────────────────────────────────────────────────


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


# ── Payloads (fetch + hash), partagés par tous les chemins ──────────────


# ── Garde-fou « données pas prêtes » ────────────────────────────────────


def _period_start(topic: str) -> datetime:
    """Début de la période d'un topic (reset quotidien ou reset du mardi)."""
    return last_reset() if topic == LOST_SECTOR_TOPIC else last_weekday_reset(TUESDAY)


def _not_ready(topic: str, reason: str) -> None:
    """Lève BungieNotReadyError tant que STALE_GRACE n'est pas écoulé, sinon
    logue et laisse publier. Le cache profil est oublié pour que la nouvelle
    tentative refasse un vrai appel API."""
    if datetime.now(timezone.utc) - _period_start(topic) >= STALE_GRACE:
        log.warning(f"[Weekly] {topic} : {reason} — délai de grâce écoulé, publication quand même.")
        return
    bungie.invalidate_character_cache()
    raise BungieNotReadyError(f"{topic} : {reason}")


def _check_fresh(state, topic: str, sig: list[str]) -> None:
    """Refuse un contenu identique à celui de la période PRÉCÉDENTE."""
    prev = state.last_signature(topic)
    if not prev or prev.get("period") == _period_start(topic).isoformat():
        return  # première publication connue, ou période déjà validée
    if prev.get("sig") == sorted(sig):
        _not_ready(topic, "contenu identique à la période précédente (données périmées ?)")


def _remember(state, topic: str, sig: list[str]) -> None:
    """Mémorise le contenu publié pour la période en cours."""
    state.set_signature(topic, _period_start(topic).isoformat(), sig)


# ── Payloads (fetch + hash), partagés par tous les chemins ──────────────
# Chaque payload renvoie (données, hash, signature) ou None si indisponible.
# `strict=True` active le garde-fou ci-dessus (pipeline uniquement).


async def _sectors_payload(state=None, *, strict: bool = False):
    sectors = await get_lost_sectors()
    if not sectors:
        if strict:
            _not_ready(LOST_SECTOR_TOPIC, "aucun secteur oublié détecté")
        return None
    sig = [str(v.activity_hash) for s in sectors for v in s.variants]
    if strict:
        _check_fresh(state, LOST_SECTOR_TOPIC, sig)
    h = content_hash([last_reset().isoformat(), *sig])
    return sectors, h, sig


def _featured_of_type(groups, activity_type: str):
    """Sous-liste featured d'un type ('Raid'/'Donjon')."""
    return [g for g in groups if g.featured and g.activity_type == activity_type]


async def _activity_payload(topic: str, activity_type: str, state, strict: bool):
    """(groups_complets, hash, signature) ou None si aucune activité featured.

    On renvoie la liste COMPLÈTE (raids + donjons) : le builder filtre par type.
    Le hash ne porte QUE sur les activités featured du type (un changement côté
    donjon ne doit pas forcer le repost du message raid)."""
    groups = await get_raid_dungeon()
    featured = _featured_of_type(groups or [], activity_type)
    if not featured:
        if strict:
            _not_ready(topic, f"aucun {activity_type.lower()} featured détecté")
        return None
    sig = [g.base_name for g in featured]
    if strict:
        _check_fresh(state, topic, sig)
    h = content_hash([last_reset().isoformat(), topic, *sig])
    return groups, h, sig


async def _raid_payload(state=None, *, strict: bool = False):
    return await _activity_payload(RAID_TOPIC, "Raid", state, strict)


async def _dungeon_payload(state=None, *, strict: bool = False):
    return await _activity_payload(DUNGEON_TOPIC, "Donjon", state, strict)


# Topics MONO-message uniquement (secteurs gérés à part, multi-message).
_TOPIC_SPECS = {
    RAID_TOPIC: (_raid_payload, build_raid_view),
    DUNGEON_TOPIC: (_dungeon_payload, build_dungeon_view),
}


# ── Secteurs oubliés : multi-message + ping final ───────────────────────


def _ls_all_ids(entry: dict) -> list:
    """IDs à supprimer pour un serveur : message_ids courants + éventuel
    message_id mono-message hérité (migration douce de l'ancien format)."""
    ids = list(entry.get("message_ids", []))
    legacy = entry.get("message_id")
    if legacy:
        ids.append(legacy)
    return ids


async def _ls_repost_guild(guild, dest, sectors, role_id, h, state, *, ping: bool) -> None:
    """Supprime les anciens messages secteurs (+ ancien ping) puis republie un
    message PAR secteur, suivi d'un message de ping rôle SEUL en dernier (si
    demandé et rôle défini). Le ping est rangé avec les message_ids."""
    guild_id = str(guild.id)
    old = state.get(guild_id, LOST_SECTOR_TOPIC)

    # 1) Supprime tout l'ancien (messages secteurs + éventuel ping + legacy).
    await _delete_messages(dest, _ls_all_ids(old))

    # 2) Republie un message par secteur (jamais de ping ici).
    new_ids: list = []
    views = await build_lost_sectors_view(sectors)
    for view, files in views:
        mid = await send_view(dest, view, files)
        if mid:
            new_ids.append(mid)
    sector_count = len(new_ids)
    # Envoi partiel → hash vide : le serveur sera retenté au prochain publish
    # au lieu d'être considéré à jour avec des secteurs manquants.
    if sector_count < len(views):
        log.warning(f"[Weekly] Secteurs : {sector_count}/{len(views)} envoyé(s) dans {guild.name}.")
        h = ""

    # 3) Ping rôle SEUL, en dernier (si demandé et rôle défini).
    if ping:
        ping_id = await send_ping(dest, role_id)
        if ping_id:
            new_ids.append(ping_id)

    # 4) Sauvegarde de l'état du serveur.
    state.set_ids(guild_id, LOST_SECTOR_TOPIC, message_ids=new_ids, content_hash=h)
    log.info(f"[Weekly] Secteurs : {sector_count} message(s) publié(s) dans {guild.name}.")


async def publish_lost_sectors(bot, state, *, ping: bool = True, strict: bool = False) -> None:
    """Secteurs oubliés du jour (multi-message).

    Purge le cache de bandeaux secteurs (cadence quotidienne) AVANT
    régénération, une fois le fetch confirmé. Saute un serveur déjà à jour pour
    ce reset (même hash + messages présents). `ping=False` reposte sans
    re-notifier (refresh manuel)."""
    payload = await _sectors_payload(state, strict=strict)
    if payload is None:
        return
    sectors, h, sig = payload
    purge_banner_cache(_FEATURE_LOST_SECTOR)

    for guild_id, dest_id, info in iter_subscribers(LOST_SECTOR_TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id, LOST_SECTOR_TOPIC)
        if saved.get("hash") == h and saved.get("message_ids"):
            continue  # déjà publié pour ce reset

        await _ls_repost_guild(guild, dest, sectors, info.get("role"), h, state, ping=ping)

    _remember(state, LOST_SECTOR_TOPIC, sig)
    state.save()


async def _restore_lost_sectors(bot, state) -> None:
    """Répare les messages secteurs disparus (sans ping).

    Si un des messages d'un serveur manque, on reconstruit TOUT ce serveur (plus
    simple et fiable). Fetch paresseux (aucun fetch si rien ne manque). Ne purge
    PAS le cache d'images (réparation = réutilisation du cache)."""
    payload = None
    fetched = False

    for guild_id, dest_id, info in iter_subscribers(LOST_SECTOR_TOPIC):
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        dest = resolve_destination(guild, dest_id, info.get("is_thread", False))
        if dest is None:
            continue

        saved = state.get(guild_id, LOST_SECTOR_TOPIC)
        ids = saved.get("message_ids", [])
        if not ids:
            continue  # jamais publié → géré au reset / à l'ajout
        if await _all_exist(dest, ids):
            continue  # tout est en place

        if not fetched:
            payload = await _sectors_payload()
            fetched = True
        if payload is None:
            continue  # fetch impossible → laissé au hold mode
        sectors, h, _ = payload
        await _ls_repost_guild(guild, dest, sectors, None, h, state, ping=False)

    state.save()


async def _ls_on_added(bot, state, guild_id, info) -> None:
    """Publie les secteurs dans un salon nouvellement configuré (avec ping)."""
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return
    dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
    if dest is None:
        return
    payload = await _sectors_payload()
    if payload is None:
        return
    sectors, h, _ = payload
    # _ls_repost_guild supprime déjà d'éventuels anciens messages mémorisés.
    await _ls_repost_guild(guild, dest, sectors, info.get("role_id"), h, state, ping=True)
    state.save()


async def _ls_on_removed(bot, state, guild_id, info) -> None:
    """Supprime tous les messages secteurs d'un salon retiré + purge l'état."""
    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await _delete_messages(dest, _ls_all_ids(state.get(guild_id, LOST_SECTOR_TOPIC)))
    state.purge(guild_id, LOST_SECTOR_TOPIC)
    state.save()


# ── Publication au reset (mono-message : raids / donjons) ────────────────


async def publish_raid(bot, state, *, ping: bool = True, strict: bool = False) -> None:
    """Raids featured de la semaine (1 message). NE PURGE PAS le cache (la
    purge est orchestrée par publish_raid_dungeon, partagée avec les donjons)."""
    payload = await _raid_payload(state, strict=strict)
    if payload is None:
        return
    groups, h, sig = payload
    await publish_persistent_view(
        bot,
        RAID_TOPIC,
        build_view=lambda data=groups: build_raid_view(data),
        content_hash=h,
        state=state,
        ping=ping,
    )
    _remember(state, RAID_TOPIC, sig)
    state.save()


async def publish_dungeon(bot, state, *, ping: bool = True, strict: bool = False) -> None:
    """Donjons featured de la semaine (1 message). NE PURGE PAS le cache (la
    purge est orchestrée par publish_raid_dungeon, partagée avec les raids)."""
    payload = await _dungeon_payload(state, strict=strict)
    if payload is None:
        return
    groups, h, sig = payload
    await publish_persistent_view(
        bot,
        DUNGEON_TOPIC,
        build_view=lambda data=groups: build_dungeon_view(data),
        content_hash=h,
        state=state,
        ping=ping,
    )
    _remember(state, DUNGEON_TOPIC, sig)
    state.save()


async def publish_raid_dungeon(bot, state, *, ping: bool = True, strict: bool = False) -> None:
    """Orchestrateur reset hebdo (mardi) : purge le cache de bandeaux
    raids/donjons UNE seule fois (cadence hebdo) PUIS publie raids puis donjons.

    La purge unique en amont évite d'effacer un bandeau fraîchement généré
    entre les deux publications (raids et donjons partagent le dossier de
    cache `raid_donjon`). `ping` et `strict` sont propagés aux deux publications."""
    purge_banner_cache(_FEATURE_RAID_DUNGEON)
    await publish_raid(bot, state, ping=ping, strict=strict)
    await publish_dungeon(bot, state, ping=ping, strict=strict)


# ── Refresh ciblé (/refresh) : purge PUIS publie un seul type, SANS ping ─


async def refresh_raid(bot, state) -> None:
    """Refresh ciblé des raids : purge le cache bandeaux (raids/donjons) PUIS
    republie les raids SANS ping. On purge car « refresh » = forcer la
    régénération des images. Le cache étant partagé avec les donjons, leurs
    bandeaux sont aussi supprimés — sans effet sur le message donjon existant
    (ses images sont déjà attachées côté Discord ; le cache est juste régénéré
    à sa prochaine publication)."""
    purge_banner_cache(_FEATURE_RAID_DUNGEON)
    await publish_raid(bot, state, ping=False)


async def refresh_dungeon(bot, state) -> None:
    """Refresh ciblé des donjons : purge le cache bandeaux (raids/donjons) PUIS
    republie les donjons SANS ping. Voir refresh_raid pour la note sur le cache
    partagé."""
    purge_banner_cache(_FEATURE_RAID_DUNGEON)
    await publish_dungeon(bot, state, ping=False)


# ── Réparation des messages disparus (sans ping) ────────────────────────


async def _restore_single(bot, state) -> None:
    """Restore MONO-message (raids/donjons) : republie SANS ping les messages
    sauvegardés qui n'existent plus. Fetch paresseux (aucun fetch si rien ne
    manque). Ne purge PAS le cache d'images."""
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
        data, h, _ = payload
        for guild_id, dest in missing:
            view, files = await build(data)
            new_mid = await send_view(dest, view, files, ping=False)
            if new_mid:
                state.set(guild_id, topic, message_id=new_mid, content_hash=h)
        state.save()


async def restore(bot, state) -> None:
    """Répare les messages weekly disparus (sans ping) : secteurs (multi-message)
    PUIS raids/donjons (mono-message). Le fetch est paresseux dans chaque
    chemin. Une BungieMaintenanceError éventuelle remonte à l'appelant (pipeline
    → hold mode)."""
    await _restore_lost_sectors(bot, state)
    await _restore_single(bot, state)


# ── Hooks /botconfig ────────────────────────────────────────────────────


async def on_added(bot, state, guild_id, topic, info) -> None:
    """Publie le contenu courant du topic dans le salon nouvellement configuré
    (avec ping). `info` = {channel_id, is_thread, role_id} (forme config).
    Ne purge PAS le cache d'images (réutilisation du cache existant).

    Secteurs → chemin multi-message dédié ; raids/donjons → mono-message."""
    if topic == LOST_SECTOR_TOPIC:
        await _ls_on_added(bot, state, guild_id, info)
        return

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
    data, h, _ = payload

    # Suppression défensive d'un éventuel ancien message mémorisé pour ce topic.
    await delete_message(dest, state.get(guild_id, topic).get("message_id"))

    view, files = await build(data)
    mid = await send_view(dest, view, files, role_id=info.get("role_id"), ping=True)
    if mid:
        state.set(guild_id, topic, message_id=mid, content_hash=h)
        state.save()


async def on_removed(bot, state, guild_id, topic, info) -> None:
    """Supprime le(s) message(s) du salon retiré et purge l'état du topic.

    Secteurs → chemin multi-message dédié ; raids/donjons → mono-message."""
    if topic == LOST_SECTOR_TOPIC:
        await _ls_on_removed(bot, state, guild_id, info)
        return

    guild = bot.get_guild(int(guild_id))
    if guild:
        dest = resolve_destination(guild, info["channel_id"], info.get("is_thread", False))
        if dest is not None:
            await delete_message(dest, state.get(guild_id, topic).get("message_id"))
    state.purge(guild_id, topic)
    state.save()