# -*- coding: utf-8 -*-
"""Routeur des changements /botconfig.

Après validation de la config, `apply_config_change` compare l'état AVANT et
APRÈS (forme load_config_state) et déclenche, par topic, les conséquences sur
les messages persistants :
- salon ajouté/changé → publier le contenu courant dans le nouveau salon
- salon retiré/changé → supprimer le(s) message(s) de l'ancien salon + purger

Un changement de salon = retrait de l'ancien PUIS ajout du nouveau. Un
changement de rôle SEUL (salon inchangé) ne déclenche rien : le nouveau rôle
prend effet au prochain repost (reset). Les topics événementiels
(maintenance_*/news_*) n'ont AUCUN hook (rien à republier/supprimer).

Les états sont les instances UNIQUES partagées (mêmes objets que le poll → pas
de seconde instance qui écrirait le même fichier en parallèle)."""
from bot.features.ada import TOPIC as ADA_TOPIC
from bot.features.ascendant.state import ascendant_state
from bot.features.distortion.state import distortion_state
from bot.features.eververse import TOPIC as EVERVERSE_TOPIC
from bot.features.vanguard import TOPIC as VANGUARD_TOPIC
from bot.features.xur.state import TOPIC as XUR_TOPIC

# Topics weekly gérés (1 message persistant chacun).
_WEEKLY_TOPICS = ("daily_lost_sector", "weekly_raid", "weekly_dungeon")


def _channel_changes(before: dict, after: dict, topics) -> list:
    """[(topic, old_channel_id, new_channel_id)] pour les topics dont le salon
    a changé entre `before` et `after` (None = pas de salon)."""
    changes = []
    for topic in topics:
        old = (before.get(topic) or {}).get("channel_id")
        new = (after.get(topic) or {}).get("channel_id")
        if old != new:
            changes.append((topic, old, new))
    return changes


async def apply_config_change(bot, guild_id, before: dict, after: dict) -> None:
    """Applique les changements de salon de `before`→`after` pour un serveur."""
    # Import différé : évite tout cycle au chargement du module de config.
    from bot.features.ada import handler as ada_handler
    from bot.features.ascendant import handler as ascendant_handler
    from bot.features.distortion import handler as distortion_handler
    from bot.features.eververse import handler as eververse_handler
    from bot.features.vanguard import handler as vanguard_handler
    from bot.features.weekly import handler as weekly_handler
    from bot.features.xur import handler as xur_handler

    # Topics weekly (secteurs, raids, donjons).
    _WEEKLY = {
        weekly_handler.LOST_SECTOR_TOPIC: weekly_handler.lost_sectors,
        weekly_handler.RAID_TOPIC: weekly_handler.raids,
        weekly_handler.DUNGEON_TOPIC: weekly_handler.dungeons,
    }
    for topic, old, new in _channel_changes(before, after, _WEEKLY_TOPICS):
        if old is not None:
            await _WEEKLY[topic].on_removed(bot, guild_id, before[topic])
        if new is not None:
            await _WEEKLY[topic].on_added(bot, guild_id, after[topic])

    # Topic Avant-garde (1 message par catégorie du Portail, état weekly).
    for topic, old, new in _channel_changes(before, after, (VANGUARD_TOPIC,)):
        if old is not None:
            await vanguard_handler.publication.on_removed(bot, guild_id, before[topic])
        if new is not None:
            await vanguard_handler.publication.on_added(bot, guild_id, after[topic])

    # Topic Xûr (statut + catégories).
    for topic, old, new in _channel_changes(before, after, (XUR_TOPIC,)):
        if old is not None:
            await xur_handler.on_removed(bot, guild_id, before[topic])
        if new is not None:
            await xur_handler.on_added(bot, guild_id, after[topic])

    # Topic Eververse (3 messages de sections).
    for topic, old, new in _channel_changes(before, after, (EVERVERSE_TOPIC,)):
        if old is not None:
            await eververse_handler.publication.on_removed(bot, guild_id, before[topic])
        if new is not None:
            await eververse_handler.publication.on_added(bot, guild_id, after[topic])

    # Topic Ada-1 (message(s) de contenu).
    for topic, old, new in _channel_changes(before, after, (ADA_TOPIC,)):
        if old is not None:
            await ada_handler.publication.on_removed(bot, guild_id, before[topic])
        if new is not None:
            await ada_handler.publication.on_added(bot, guild_id, after[topic])

    # Topic Distorsion (cog dédié, édition en place — aucun ping).
    for topic, old, new in _channel_changes(before, after, ("distortion",)):
        if old is not None:
            await distortion_handler.on_removed(bot, distortion_state(), guild_id, before[topic])
        if new is not None:
            await distortion_handler.on_added(bot, distortion_state(), guild_id, after[topic])

    # Topic Défis ascendants (cog dédié, édition en place — aucun ping).
    for topic, old, new in _channel_changes(before, after, ("ascendant",)):
        if old is not None:
            await ascendant_handler.on_removed(bot, ascendant_state(), guild_id, before[topic])
        if new is not None:
            await ascendant_handler.on_added(bot, ascendant_state(), guild_id, after[topic])