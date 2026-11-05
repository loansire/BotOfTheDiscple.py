# -*- coding: utf-8 -*-
"""Publication Avant-garde (activités du Portail en focus du jour).

Moteur multi-message partagé : cf. bot/publishing/repost.py. Un message par
catégorie (Escouade, Prestige, Arène, Solo), puis le ping rôle seul. L'état
vit en base sous le topic `daily_vanguard` (cf. bot/features/weekly/state.py).

Calcul (presenter.py) → base → publication depuis la base. Le contenu porte
la ligne « Actualisation » : repost quotidien, mais un serveur déjà à jour
dans la même journée n'est pas reposté. En mode `strict` (pipeline au reset),
le garde-fou « données pas prêtes » s'applique (cf.
bot/features/weekly/freshness.py) ; la signature validée est mémorisée dès le
calcul."""
from __future__ import annotations

from bot.bungie.reset import TUESDAY, last_reset, last_weekday_reset
from bot.compute import purge_icons_once_per_reset, store
from bot.content.model import Post
from bot.features.vanguard import TOPIC, get_portal
from bot.features.vanguard.filters import challenges_of
from bot.features.vanguard.presenter import FEATURE, build_vanguard_views
from bot.features.weekly.freshness import check_fresh, not_ready, remember
from bot.features.weekly.state import weekly_slot, weekly_state
from bot.publishing.content_source import stored_payload, stored_views
from bot.publishing.repost import RepostTopic

TAG = "Avant-garde"


async def produce(strict: bool = False) -> bool:
    """Calcule les catégories du Portail et les range en base. False si rien
    n'est détecté.

    Les défis (hebdomadaires) vus une fois dans la semaine sont mémorisés et
    réaffichés aux resets quotidiens suivants, même une fois accomplis sur le
    personnage de référence (le profil ne les montre plus)."""
    state = weekly_state()
    week = last_weekday_reset(TUESDAY).isoformat()
    remembered = state.week_challenges(week)
    categories = await get_portal(remembered)
    seen = challenges_of(categories)
    if categories and seen != remembered:
        state.set_week_challenges(week, {**remembered, **seen})
        await state.save()

    sig = [f"{a.base_name}|{a.focus_hash}" for c in categories for a in c.activities]
    if not sig:
        if strict:
            not_ready(TOPIC, "aucune activité en focus détectée")
        return False
    if strict:
        check_fresh(state, TOPIC, sig)
        remember(state, TOPIC, sig)

    purge_icons_once_per_reset(FEATURE)
    messages = await build_vanguard_views(categories)
    await store(Post(TOPIC, "repost", {"default": messages}, period_start=last_reset()), TAG)
    return True


publication = RepostTopic(
    topic=TOPIC,
    tag=TAG,
    state=lambda: weekly_slot(TOPIC),
    payload=stored_payload(TOPIC, produce),
    build_views=stored_views,
)
