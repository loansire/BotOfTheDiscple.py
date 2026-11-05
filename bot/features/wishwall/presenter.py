# -*- coding: utf-8 -*-
"""Calcul du Wishwall (/wish-wall), rangé en base (topic `wishwall`).

Variante `intro` + une variante par vœu (`0`, `1`...) : embed (description,
image du vœu ou image par défaut, vignette, pied de page) et le menu de
sélection (custom_id `wishwall:select`, une option par vœu). Le menu relit la
variante choisie en base."""
from __future__ import annotations

from bot.compute import mime_of, read_resource
from bot.content.model import EMBED, Component, Message, Post, image
from bot.features.wishwall.service import (
    DEFAULT_IMAGE,
    FOOTER_ICON_PATH,
    THUMBNAIL_PATH,
    WISHES_DIR,
    load_wishes,
)

TOPIC = "wishwall"
INTRO = "intro"
SELECT_ID = "wishwall:select"
_COLOR = 0x6E00F5


def _stored(kind: str, path, name: str, **extra) -> list[Component]:
    data = read_resource(path)
    if data is None:
        return [Component(kind, **extra)] if extra else []
    return [image(kind, data, name, mime=mime_of(path), **extra)]


def _message(description: str, image_file: str, wishes: list[dict]) -> Message:
    path = WISHES_DIR / image_file
    if read_resource(path) is None:
        path = WISHES_DIR / DEFAULT_IMAGE
    message = Message(layout=EMBED, accent_color=_COLOR)
    message.add(Component("embed_description", text=description))
    for component in (
        *_stored("embed_image", path, path.name),
        *_stored("embed_thumbnail", THUMBNAIL_PATH, "thumbnail.png"),
        *_stored("embed_footer", FOOTER_ICON_PATH, "footer_icon.png", text="BotOfTheDisciple"),
    ):
        message.add(component)
    message.add(Component("select", title="Sélectionnez un vœu...", btn_action=SELECT_ID))
    for i, wish in enumerate(wishes):
        label = wish.get("BoutonName") or wish["nom"].split(" - ")[-1]
        message.add(Component("option", btn_label=label, btn_action=str(i)))
    return message


def build_post() -> Post:
    wishes = load_wishes()
    variants = {INTRO: [_message(
        "## Wishwall\nSélectionnez un vœu dans le menu déroulant pour voir les détails.",
        DEFAULT_IMAGE, wishes,
    )]}
    for i, wish in enumerate(wishes):
        variants[str(i)] = [_message("## " + wish["nom"] + "\n" + wish["description"], wish["image"], wishes)]
    return Post(TOPIC, "on_demand", variants)
