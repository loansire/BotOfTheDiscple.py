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

Les états sont récupérés en mémoire via le cog Pipeline (mêmes objets que le
poll → pas de seconde instance qui écrirait le même fichier en parallèle)."""
from bot.features.ada import TOPIC as ADA_TOPIC
from bot.features.eververse import TOPIC as EVERVERSE_TOPIC
from bot.features.xur.state import TOPIC as XUR_TOPIC
from bot.utils.logger import log

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
    pipeline = bot.get_cog("Pipeline")
    if pipeline is None:
        log.warning("[Config] Cog Pipeline introuvable — changements non appliqués.")
        return

    # Import différé : évite tout cycle au chargement du module de config.
    from bot.discord.handlers import ada as ada_handler
    from bot.discord.handlers import eververse as eververse_handler
    from bot.discord.handlers import weekly as weekly_handler
    from bot.discord.handlers import xur as xur_handler

    weekly_state = pipeline.weekly_state
    xur_state = pipeline.xur_state
    eververse_state = pipeline.eververse_state
    ada_state = pipeline.ada_state

    # Topics weekly (secteurs, raids, donjons).
    for topic, old, new in _channel_changes(before, after, _WEEKLY_TOPICS):
        if old is not None:
            await weekly_handler.on_removed(bot, weekly_state, guild_id, topic, before[topic])
        if new is not None:
            await weekly_handler.on_added(bot, weekly_state, guild_id, topic, after[topic])

    # Topic Xûr (statut + catégories).
    for topic, old, new in _channel_changes(before, after, (XUR_TOPIC,)):
        if old is not None:
            await xur_handler.on_removed(bot, xur_state, guild_id, before[topic])
        if new is not None:
            await xur_handler.on_added(bot, xur_state, guild_id, after[topic])

    # Topic Eververse (3 messages de sections).
    for topic, old, new in _channel_changes(before, after, (EVERVERSE_TOPIC,)):
        if old is not None:
            await eververse_handler.on_removed(bot, eververse_state, guild_id, before[topic])
        if new is not None:
            await eververse_handler.on_added(bot, eververse_state, guild_id, after[topic])

    # Topic Ada-1 (message(s) de contenu).
    for topic, old, new in _channel_changes(before, after, (ADA_TOPIC,)):
        if old is not None:
            await ada_handler.on_removed(bot, ada_state, guild_id, before[topic])
        if new is not None:
            await ada_handler.on_added(bot, ada_state, guild_id, after[topic])

    # Topic Distorsion (cog dédié, édition en place — aucun ping).
    distortion = bot.get_cog("Distortion")
    if distortion is not None:
        from bot.discord.handlers import distortion as distortion_handler
        d_old = (before.get("distortion") or {}).get("channel_id")
        d_new = (after.get("distortion") or {}).get("channel_id")
        if d_old != d_new:
            if d_old is not None:
                await distortion_handler.on_removed(bot, distortion.state, guild_id, before["distortion"])
            if d_new is not None:
                await distortion_handler.on_added(bot, distortion.state, guild_id, after["distortion"])