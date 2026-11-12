# -*- coding: utf-8 -*-
"""Publication Xûr (sans @tasks.loop ni calcul).

Appelée par la pipeline (cogs/pipeline.py) et le routeur /botconfig
(bot/publishing/router.py) :
- publish_arrival       : VENDREDI — supprime TOUT puis republie TOUT (statut +
  catégories) par serveur, suivi d'un message de ping rôle SEUL en dernier (si
  un rôle est défini). `ping=False` (refresh manuel) reposte sans notifier.
- mark_departed         : MARDI — supprime les catégories (et le ping), édite le
  statut en « n'est pas là » (édition in-place → aucune notification).
- restore               : répare les messages disparus (sans ping), au reset.
- on_added / on_removed : ajout/retrait d'un salon via /botconfig.
- refresh_absent_status : utilitaire /refresh hors fenêtre Xûr.

Contenu lu en base (topics `xur` et `xur_status`). Le bot qui calcule (live)
branche ses étapes de calcul via bot/publishing/producers.py : inventaire
(`xur`, appelé seulement par publish_arrival / on_added / restore-actif, jamais
le mardi) et statut (`xur_status`). Sans calcul enregistré (lite), on publie
la dernière version en base.

Ping rôle : un message à part, envoyé en DERNIER (send_ping), seulement si un
rôle est défini. Son id est rangé dans `category_ids` (messages jetables) : il
est supprimé au repost et au départ du mardi, comme les catégories."""
from __future__ import annotations

from types import SimpleNamespace

import discord

from bot.content.keys import XUR_ABSENT as ABSENT
from bot.content.keys import XUR_PRESENT as PRESENT
from bot.content.keys import XUR_STATUS_TOPIC as STATUS_TOPIC
from bot.content.keys import XUR_TOPIC as TOPIC
from bot.core.logger import log
from bot.core.reset import is_xur_active
from bot.publishing import producers
from bot.publishing.content_source import snapshot, stored_views
from bot.publishing.primitives import (
    all_exist,
    config_destination,
    delete_messages,
    destinations_by_guild,
    iter_destinations,
    message_exists,
    send_ping,
    send_view,
)
from bot.publishing.states import xur_state


# ── Helpers ─────────────────────────────────────────────────────────────


def _known_destinations(bot, state):
    """(guild_id, guild, dest, entry) des serveurs DÉJÀ publiés (présents dans
    l'état) et toujours abonnés/joignables."""
    dests = destinations_by_guild(bot, TOPIC)
    for guild_id, entry in state.iter_guilds():
        if guild_id in dests:
            guild, dest = dests[guild_id]
            yield guild_id, guild, dest, entry


async def _fetch_vendors():
    """Inventaire de la semaine (Snapshot du topic `xur`), recalculé au
    passage par le bot qui calcule ; None si indisponible/vide."""
    produce = producers.get(TOPIC)
    if produce is not None and not await produce():
        return None
    return await snapshot(TOPIC)


async def _status_view(present: bool):
    """Vue du message statut, lue en base (variante « présent » ou
    « absent » du topic `xur_status`, recalculé au passage)."""
    produce = producers.get(STATUS_TOPIC)
    if produce is not None:
        await produce()
    snap = await snapshot(STATUS_TOPIC, PRESENT if present else ABSENT)
    return snap.render().view


def _xur_hash(vendors) -> str:
    """Hash de l'inventaire en base (tout le contenu rendu)."""
    return vendors.hash


# ── VENDREDI : arrivée ──────────────────────────────────────────────────


async def publish_arrival(bot, *, ping: bool = True) -> None:
    """Xûr arrive : par serveur, supprime tout puis republie statut, catégories,
    puis un message de ping rôle seul en dernier. Saute un serveur déjà à jour
    pour ce reset (évite de re-pinger tout le monde si on republie pour un seul
    serveur).

    `ping=False` (refresh manuel) reposte sans envoyer le message de mention."""
    state = xur_state()
    vendors = await _fetch_vendors()
    if vendors is None:
        log.warning("[Xûr] Aucun item récupéré — arrivée non publiée.")
        return

    xur_hash = _xur_hash(vendors)

    for guild_id, guild, dest, info in iter_destinations(bot, TOPIC):
        saved = state.get(guild_id)
        if saved["hash"] == xur_hash and saved["status_id"] and saved["category_ids"]:
            continue  # déjà publié pour ce reset

        await _repost_guild(
            guild, dest, vendors, info.get("role"), xur_hash, state, ping=ping
        )

    await state.save()


async def _repost_guild(
    guild, dest, vendors, role_id, xur_hash, state, *, ping: bool = True
) -> None:
    """Supprime tout (statut + catégories + ancien ping) puis republie. `ping`
    n'agit que sur le message de ping final (jamais sur le statut ni les
    catégories).

    Le ping est un message à part (mention seule), posté en DERNIER et seulement
    si un rôle est défini. Son id est rangé avec les catégories (messages
    jetables) → supprimé/reposté avec elles, et supprimé au départ du mardi."""
    guild_id = str(guild.id)
    old = state.get(guild_id)

    # 1) Supprime TOUT (ancien statut + anciennes catégories + ancien ping).
    to_delete = ([old["status_id"]] if old["status_id"] else []) + old["category_ids"]
    await delete_messages(dest, to_delete)

    # 2) Nouveau statut « est là » (jamais de ping ici).
    status_view = await _status_view(True)
    status_id = await send_view(dest, status_view)
    if status_id is None:
        return  # rien de cohérent à enregistrer

    # 3) Catégories (jamais de ping : le ping est un message à part).
    new_ids: list = []
    views = await stored_views(vendors)
    for view, files in views:
        mid = await send_view(dest, view, files)
        if mid:
            new_ids.append(mid)
    category_count = len(new_ids)
    # Envoi partiel → hash vide : le serveur sera retenté au prochain publish.
    if category_count < len(views):
        log.warning(f"[Xûr] {category_count}/{len(views)} catégorie(s) envoyée(s) dans {guild.name}.")
        xur_hash = ""

    # 4) Ping rôle SEUL, en dernier (si demandé et rôle défini). Rangé avec les
    #    catégories → supprimé/reposté avec elles.
    if ping:
        ping_id = await send_ping(dest, role_id)
        if ping_id:
            new_ids.append(ping_id)

    # 5) Sauvegarde de l'état du serveur.
    state.set(guild_id, status_id=status_id, category_ids=new_ids, content_hash=xur_hash)
    log.info(f"[Xûr] Statut + {category_count} catégorie(s) publié(s) dans {guild.name}.")


# ── MARDI : départ ──────────────────────────────────────────────────────


async def mark_departed(bot) -> None:
    """Xûr part : supprime les catégories (et le message de ping) et édite le
    statut en « n'est pas là » (édition in-place → aucune notification). Aucun
    appel vendor."""
    state = xur_state()

    for guild_id, guild, dest, entry in _known_destinations(bot, state):
        await delete_messages(dest, entry["category_ids"])
        state.clear_categories(guild_id)

        status_view = await _status_view(False)
        await _edit_or_post_status(dest, guild, status_view, state)

    await state.save()


async def _edit_or_post_status(dest, guild, status_view, state) -> None:
    """Édite le statut « absent » existant ; s'il a disparu, le reposte SANS ping."""
    guild_id = str(guild.id)
    status_id = state.status_id(guild_id)
    if status_id:
        try:
            msg = await dest.fetch_message(int(status_id))
            await msg.edit(view=status_view)
            log.info(f"[Xûr] Statut « absent » édité dans {guild.name}.")
            return
        except discord.NotFound:
            log.warning(f"[Xûr] Statut {status_id} introuvable (guild {guild_id}) — repost.")
        except discord.DiscordException as e:
            log.error(f"[Xûr] Édition statut échouée (guild {guild_id}) : {e}")
            return

    mid = await send_view(dest, status_view, ping=False)
    if mid:
        state.set(guild_id, status_id=mid)
        log.info(f"[Xûr] Statut « absent » reposté dans {guild.name}.")


# ── Réparation des messages disparus (point 4, sans ping) ───────────────


async def restore(bot) -> None:
    """Répare les messages Xûr disparus (sans ping).

    Xûr actif : si le statut OU une catégorie (ou le ping) manque pour un
    serveur, on reconstruit TOUT ce serveur (plus simple et fiable). Le fetch
    vendor est paresseux (aucun fetch si rien ne manque). Xûr inactif : seul le
    statut « absent » doit exister ; on le rétablit au besoin, sans fetch."""
    state = xur_state()
    active = is_xur_active()
    vendors = None
    vendors_fetched = False

    for guild_id, guild, dest, entry in _known_destinations(bot, state):
        status_ok = (
            await message_exists(dest, entry["status_id"]) if entry["status_id"] else False
        )

        if active:
            cats_ok = bool(entry["category_ids"]) and await all_exist(
                dest, entry["category_ids"]
            )
            if status_ok and cats_ok:
                continue
            if not vendors_fetched:
                vendors = await _fetch_vendors()
                vendors_fetched = True
            if vendors is None:
                continue  # fetch impossible → laissé au Lot 4
            await _repost_guild(
                guild, dest, vendors, None, _xur_hash(vendors), state, ping=False
            )
        else:
            if status_ok:
                if entry["category_ids"]:
                    await delete_messages(dest, entry["category_ids"])
                    state.clear_categories(guild_id)
                continue
            status_view = await _status_view(False)
            await _edit_or_post_status(dest, guild, status_view, state)

    await state.save()


# ── Hooks /botconfig ────────────────────────────────────────────────────


async def on_added(bot, guild_id, info) -> None:
    """Ajout d'un salon Xûr. `info` = {channel_id, is_thread, role_id}.
    Xûr actif → statut + catégories + message de ping seul en dernier ; inactif
    → statut absent (sans ping)."""
    state = xur_state()
    target = config_destination(bot, guild_id, info)
    if target is None:
        return
    guild, dest = target
    role_id = info.get("role_id")

    if is_xur_active():
        vendors = await _fetch_vendors()
        if vendors is None:
            # Actif mais fetch indisponible : poste le statut SEUL, sans ping
            # (inutile de notifier sans items). category_ids reste vide → restore
            # retentera la publication complète au rétablissement de l'API.
            status_view = await _status_view(True)
            mid = await send_view(dest, status_view)
            if mid:
                state.set(guild_id, status_id=mid, category_ids=[], content_hash="")
                await state.save()
                log.info(f"[Xûr] Statut seul publié dans {guild.name} (inventaire indisponible).")
            return
        await _repost_guild(
            guild, dest, vendors, role_id, _xur_hash(vendors), state, ping=True
        )
        await state.save()
    else:
        status_view = await _status_view(False)
        mid = await send_view(dest, status_view, ping=False)
        if mid:
            state.set(guild_id, status_id=mid, category_ids=[], content_hash="")
            await state.save()
            log.info(f"[Xûr] Statut « absent » publié dans {guild.name} (nouveau salon).")


async def on_removed(bot, guild_id, info) -> None:
    """Retrait d'un salon Xûr : supprime statut + catégories (+ ping), purge
    l'état."""
    state = xur_state()
    target = config_destination(bot, guild_id, info)
    if target is not None:
        entry = state.get(guild_id)
        to_delete = ([entry["status_id"]] if entry["status_id"] else []) + entry["category_ids"]
        await delete_messages(target[1], to_delete)
    state.purge(guild_id)
    await state.save()


# ── /refresh hors fenêtre Xûr ────────────────────────────────────────────


async def refresh_absent_status(bot) -> None:
    """Met le statut à « n'est pas là » et purge d'éventuelles catégories
    (ou ping) résiduelles. Utilisé par /refresh quand Xûr est inactif."""
    state = xur_state()

    for guild_id, guild, dest, entry in _known_destinations(bot, state):
        if entry["category_ids"]:
            await delete_messages(dest, entry["category_ids"])
            state.clear_categories(guild_id)

        status_view = await _status_view(False)
        await _edit_or_post_status(dest, guild, status_view, state)

    await state.save()


async def refresh(bot) -> None:
    """/refresh : force le repost SANS ping (Xûr présent), ou remet le statut
    « absent » par édition in-place (aucune notification)."""
    await xur_state().invalidate()
    if is_xur_active():
        await publish_arrival(bot, ping=False)
    else:
        await refresh_absent_status(bot)


# Interface commune des publications (cf. bot/publishing/registry.py).
publication = SimpleNamespace(
    tag="Xûr",
    restore=restore,
    on_added=on_added,
    on_removed=on_removed,
    refresh=refresh,
)
