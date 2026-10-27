# -*- coding: utf-8 -*-
"""Publication Avant-garde (activités du Portail en focus du jour).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Un message par
catégorie (Escouade, Prestige, Arène, Solo), puis le ping rôle seul. L'état
vit dans WeeklyMessageState sous le topic `daily_vanguard` (vue TopicSlot).

Le hash inclut le reset courant : repost quotidien, mais un serveur déjà à
jour dans la même journée n'est pas reposté. En mode `strict` (pipeline au
reset), le garde-fou « données pas prêtes » s'applique (cf.
bot/features/weekly/freshness.py)."""
from __future__ import annotations

from bot.bungie.reset import TUESDAY, last_reset, last_weekday_reset
from bot.features.vanguard import TOPIC, get_portal
from bot.features.vanguard.filters import challenges_of
from bot.features.vanguard.view import FEATURE, build_vanguard_views
from bot.features.weekly.freshness import check_fresh, not_ready, remember
from bot.features.weekly.state import weekly_slot, weekly_state
from bot.publishing.primitives import content_hash
from bot.publishing.repost import Payload, RepostTopic
from bot.render.banner import purge_banner_cache


async def _payload(strict: bool) -> Payload | None:
    """Catégories du Portail, ou None si rien n'est détecté.

    Les défis (hebdomadaires) vus une fois dans la semaine sont mémorisés dans
    l'état et réaffichés aux resets quotidiens suivants, même une fois
    accomplis sur le personnage de référence (le profil ne les montre plus)."""
    state = weekly_state()
    week = last_weekday_reset(TUESDAY).isoformat()
    remembered = state.week_challenges(week)
    categories = await get_portal(remembered)
    seen = challenges_of(categories)
    if categories and seen != remembered:
        state.set_week_challenges(week, {**remembered, **seen})
        state.save()

    sig = [f"{a.base_name}|{a.focus_hash}" for c in categories for a in c.activities]
    if not sig:
        if strict:
            not_ready(TOPIC, "aucune activité en focus détectée")
        return None
    if strict:
        check_fresh(state, TOPIC, sig)
    return Payload(categories, content_hash([last_reset().isoformat(), TOPIC, *sig]), sig)


publication = RepostTopic(
    topic=TOPIC,
    tag="Avant-garde",
    state=lambda: weekly_slot(TOPIC),
    payload=_payload,
    build_views=build_vanguard_views,
    purge_cache=lambda: purge_banner_cache(FEATURE),
    on_published=lambda p: remember(weekly_state(), TOPIC, p.sig),
)
