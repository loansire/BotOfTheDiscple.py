# -*- coding: utf-8 -*-
"""Topic → publication persistante (pendant de bot/topics.py).

Les publications ne calculent rien : elles publient la dernière version
rangée en base. Le bot qui calcule (live) branche ses étapes de calcul via
bot/publishing/producers.py ; un bot qui ne fait que publier (lite) utilise
ce catalogue tel quel.

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

from bot.publishing import xur as _xur
from bot.publishing.content_source import stored_payload, stored_views
from bot.publishing.edit_in_place import EditInPlaceTopic
from bot.publishing.repost import RepostTopic
from bot.publishing.single import SingleTopic
from bot.publishing.states import multi_state, single_state

_EMPTY = "Aucun item récupéré — publication annulée."


def _repost(topic: str, tag: str, empty_warning: str | None = None) -> RepostTopic:
    return RepostTopic(
        topic=topic,
        tag=tag,
        state=lambda: multi_state(topic),
        payload=stored_payload(topic),
        build_views=stored_views,
        empty_warning=empty_warning,
    )


async def _single_view(snap) -> tuple:
    out = snap.render()
    return out.view, out.files


def _single(topic: str, tag: str) -> SingleTopic:
    return SingleTopic(
        topic=topic,
        tag=tag,
        state=lambda: single_state(topic),
        payload=stored_payload(topic),
        build_view=_single_view,
    )


def _edit_in_place(topic: str, tag: str) -> EditInPlaceTopic:
    return EditInPlaceTopic(topic=topic, tag=tag, state=lambda: single_state(topic))


lost_sectors = _repost("daily_lost_sector", "Secteurs")
raids = _single("weekly_raid", "Raids")
dungeons = _single("weekly_dungeon", "Donjons")
vanguard = _repost("daily_vanguard", "Avant-garde")
xur = _xur.publication
eververse = _repost("eververse", "Eververse", _EMPTY)
ada = _repost("ada", "Ada-1", _EMPTY)
distortion = _edit_in_place("distortion", "Distortion")
ascendant = _edit_in_place("ascendant", "Ascendant")


@cache
def publications() -> dict:
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
