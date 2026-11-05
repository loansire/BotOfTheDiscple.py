# -*- coding: utf-8 -*-
"""Calcul des publications News (embeds), rangées en base.

Un topic par type d'alerte (`news_twid`, `news_patch_note`), deux variantes :
`en` (toujours) et `fr` (dès que Bungie publie une traduction réellement en
français). Chaque variante porte ses boutons EN / FR (+ 🔄 tant que le FR
manque) : un clic relit la variante en base, sans appel à Bungie."""
from __future__ import annotations

from bot.bungie.client import BUNGIE_BASE
from bot.compute import read_resource
from bot.content.model import EMBED, Component, Message, Post, button, image
from bot.core.config import RESOURCES_DIR

FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"
EN, FR, CHECK = "en", "fr", "check"


def action(topic: str, what: str) -> str:
    return f"news:{topic}:{what}"


def _buttons(topic: str, language: str, both: bool) -> list[Component]:
    if language == FR and both:
        en_style, fr_style = "secondary", "success"
    else:
        en_style, fr_style = "success", ("secondary" if both else "danger")
    out = [
        button("EN", action(topic, EN), emoji="🇺🇸", style=en_style),
        button("FR", action(topic, FR), emoji="🇫🇷", style=fr_style, disabled=not both),
    ]
    if not both:
        out.append(button(None, action(topic, CHECK), emoji="🔄"))
    return out


def _message(topic: str, article: dict, language: str, both: bool) -> Message:
    title = article.get("Title", "Sans titre")
    description = article.get("Description", "Pas de description disponible")
    url = f"{BUNGIE_BASE}{article.get('Link', '#')}"
    message = Message(layout=EMBED, accent_color=0x992D22)  # discord.Color.dark_red()
    message.add(Component("embed_description", text=f"## [{title}]({url})\n{description}"))
    if article.get("ImagePath"):
        message.add(Component("embed_image", image_url=article["ImagePath"]))
    footer = article.get("PubDate", "Date inconnue")
    data = read_resource(FOOTER_ICON_PATH)
    if data is None:
        message.add(Component("embed_footer", text=footer))
    else:
        message.add(image("embed_footer", data, "footer_icon.png", mime="image/png", text=footer))
    for component in _buttons(topic, language, both):
        message.add(component)
    return message


def build_post(topic: str, article_en: dict, article_fr: dict | None) -> Post:
    both = article_fr is not None
    variants = {EN: [_message(topic, article_en, EN, both)]}
    if both:
        variants[FR] = [_message(topic, article_fr, FR, both)]
    return Post(topic, "event", variants)
