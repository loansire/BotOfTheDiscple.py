# -*- coding: utf-8 -*-
"""Routeur des changements /botconfig.

Après validation de la config, `apply_config_change` compare l'état AVANT et
APRÈS (forme load_config_state) et déclenche, par topic persistant (cf.
bot/publishing/registry.py), les conséquences sur ses messages :
- salon ajouté/changé → publier le contenu courant dans le nouveau salon ;
- salon retiré/changé → supprimer le(s) message(s) de l'ancien salon + purger.

Un changement de salon = retrait de l'ancien PUIS ajout du nouveau. Un
changement de rôle SEUL (salon inchangé) ne déclenche rien : le nouveau rôle
prend effet au prochain repost (reset). Les topics événementiels
(maintenance_*/news_*) n'ont AUCUN hook.

Chaque topic est isolé : l'échec de l'un n'empêche pas d'appliquer les autres."""
from bot.core.logger import log
from bot.publishing.registry import publications


def _channel(state: dict, topic: str):
    return (state.get(topic) or {}).get("channel_id")


async def apply_config_change(bot, guild_id, before: dict, after: dict) -> None:
    """Applique les changements de salon de `before`→`after` pour un serveur."""
    for topic, publication in publications().items():
        old, new = _channel(before, topic), _channel(after, topic)
        if old == new:
            continue
        try:
            if old is not None:
                await publication.on_removed(bot, guild_id, before[topic])
            if new is not None:
                await publication.on_added(bot, guild_id, after[topic])
        except Exception as e:
            log.error(f"[Config] {topic} : application du changement de salon échouée : {e}")
