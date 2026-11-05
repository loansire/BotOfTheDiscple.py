# -*- coding: utf-8 -*-
"""Calcul des publications Maintenance (embeds), rangées en base.

- topic `maintenance_<jeu>` : l'annonce (variante `default`) + le texte prêt
  à copier (variante `copy`, lu par le bouton « Copier les infos ») ;
- topic `maintenance_<jeu>_end` : le message de fin.

Tout est figé au calcul : vignette tirée au hasard UNE fois (identique sur
tous les serveurs), date du pied de page, lien de l'article."""
from __future__ import annotations

import random
from datetime import datetime

from bot.compute import read_resource
from bot.content.model import EMBED, Component, Message, Post, button, image, text
from bot.core.config import RESOURCES_DIR
from bot.features.maintenance.fetcher import ARTICLES
from bot.features.maintenance.formatter import GAME_LABELS
from bot.features.maintenance.models import resolve_game

MAINTENANCE_DIR = RESOURCES_DIR / "Maintenance"
FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"
COPY = "copy"

# Métadonnées d'affichage par jeu
GAME_META = {
    "destiny": {
        "article_locale": "en-us",
        "author_name": "@help.bungie.net | Généré par BotOfTheDisciple",
        "author_url": "https://help.bungie.net",
        "emoji_id": "710283624619966484",
        "thumb_dir": "Destiny2",
        "thumb_count": 11,
    },
    "marathon": {
        "article_locale": "en-us",
        "author_name": "@help.marathonthegame | Généré par BotOfTheDisciple",
        "author_url": "https://help.marathonthegame.com",
        "emoji_id": "1111270580923142164",
        "thumb_dir": "Marathon",
        "thumb_count": 1,
    },
}


def topic_of(game: str) -> str:
    return f"maintenance_{game}"


def end_topic_of(game: str) -> str:
    return f"maintenance_{game}_end"


def copy_action(game: str) -> str:
    return f"maintenance:copy:{game}"


def _article_link(game: str) -> str:
    """URL publique de l'article depuis l'id défini dans fetcher."""
    cfg = ARTICLES[resolve_game(game)]
    locale = GAME_META[game]["article_locale"]
    return f"{cfg['base_url']}/hc/{locale}/articles/{cfg['article_id']}"


def _author(game: str) -> list[Component]:
    meta = GAME_META.get(game)
    if not meta:
        return []
    return [Component(
        "embed_author", title=meta["author_name"], url=meta["author_url"],
        image_url=f"https://cdn.discordapp.com/emojis/{meta['emoji_id']}.png",
    )]


def _footer() -> Component:
    footer = f"BotOfTheDisciple • {datetime.now().strftime('%Y/%m/%d %H:%M')}"
    data = read_resource(FOOTER_ICON_PATH)
    if data is None:
        return Component("embed_footer", text=footer)
    return image("embed_footer", data, "footer_icon.png", mime="image/png", text=footer)


def build_announcement_post(window: dict, copy_text: str | None = None) -> Post:
    game = window["game"]
    label = window["game_label"]
    off = window["offline_unix"]
    on = window.get("online_unix")
    meta = GAME_META.get(game, {})
    link = _article_link(game) if meta else ""

    message = Message(layout=EMBED, accent_color=0xFF0000, components=_author(game))
    message.add(Component("embed_description", text=(
        f"## [Infos de Maintenance {label}]({link})\n"
        f"*Dernières informations concernant la maintenance de {label}.*\n"
    )))
    if window.get("event_type"):
        message.add(Component("embed_field", title="📝 __Commentaire(s)__", text=window["event_type"], inline_field=False))
    message.add(Component("embed_field", title=":x: __Stop serveurs__", text=f"<t:{off}:t>", inline_field=True))
    if on:
        message.add(Component("embed_field", title=":white_check_mark: __Retour serveurs__", text=f"<t:{on}:t>", inline_field=True))
    message.add(Component("embed_field", title=":repeat: __Débute__", text=f"**<t:{off}:R>**", inline_field=False))

    if meta:
        n = random.randint(1, meta["thumb_count"])
        data = read_resource(MAINTENANCE_DIR / meta["thumb_dir"] / f"thumbnail_maintenance_{n}.png")
        if data is not None:
            message.add(image("embed_thumbnail", data, "thumb.png", mime="image/png"))
    message.add(_footer())

    variants = {"default": [message]}
    if copy_text:
        message.add(button("Copier les infos", copy_action(game), emoji="💾", style="primary"))
        variants[COPY] = [Message().add(text(copy_text))]
    return Post(topic_of(game), "event", variants)


def build_end_post(game: str) -> Post:
    label = GAME_LABELS.get(game, game.title())
    link = _article_link(game) if GAME_META.get(game) else ""
    message = Message(layout=EMBED, accent_color=0x2ECC71, components=_author(game))
    message.add(Component("embed_description", text=(
        f"## [Maintenance {label} terminée]({link})\n"
        f"*Les serveurs de {label} sont de retour. Bon jeu !*\n"
    )))
    message.add(_footer())
    return Post(end_topic_of(game), "event", {"default": [message]})
