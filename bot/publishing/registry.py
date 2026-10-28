# -*- coding: utf-8 -*-
"""Topic → publication persistante (pendant de bot/topics.py).

Toute publication expose la même interface :
    restore(bot)                        réparation sans ping (fin de reset)
    on_added(bot, guild_id, info)       salon ajouté via /botconfig
    on_removed(bot, guild_id, info)     salon retiré via /botconfig
    refresh(bot)                        /refresh (sans ping)

Les topics événementiels (news_*, maintenance_*) n'y figurent pas : rien à
republier ni supprimer. L'ordre du dictionnaire est l'ordre d'application
(routeur /botconfig, réparation, « Tout » dans /refresh).

Les rotations fixes (distortion, ascendant) n'ont pas de restore : leur poll
à la minute répare déjà les messages disparus."""
from __future__ import annotations

from functools import cache


@cache
def publications() -> dict:
    # Import différé : ce module est chargé par le routeur /botconfig et la
    # pipeline, qui ne doivent pas entraîner toutes les features au chargement.
    from bot.features.ada.handler import publication as ada
    from bot.features.ascendant.handler import publication as ascendant
    from bot.features.distortion.handler import publication as distortion
    from bot.features.eververse.handler import publication as eververse
    from bot.features.vanguard.handler import publication as vanguard
    from bot.features.weekly.handler import dungeons, lost_sectors, raids
    from bot.features.xur.handler import publication as xur

    return {
        "daily_lost_sector": lost_sectors,
        "weekly_raid": raids,
        "weekly_dungeon": dungeons,
        "daily_vanguard": vanguard,
        "xur": xur,
        "eververse": eververse,
        "ada": ada,
        "distortion": distortion,
        "ascendant": ascendant,
    }
