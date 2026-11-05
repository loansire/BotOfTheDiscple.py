# -*- coding: utf-8 -*-
"""Calcul de la publication Eververse (Components V2).

Normalement un message par section (dans l'ordre) : titre (emoji Tess +
libellé) + actualisation (prochain reset quotidien) sur CHAQUE message,
séparateur, puis une section par item (nom, libellé de classe pour les
ornements d'armure, coût en Poussière brillante ; icône composée à droite).
Une section qui dépasse le plafond CV2 est re-découpée (« (n/total) »)."""
from __future__ import annotations

from bot.bungie.reset import last_reset, next_reset
from bot.compute import item_section
from bot.content.model import Message, Post, separator, text
from bot.features.eververse import TOPIC
from bot.features.eververse.constants import DUST_EMOJI, TESS_EMOJI
from bot.features.eververse.models import EververseSection
from bot.render.layout import chunked, refresh_line

FEATURE = "eververse"  # sous-dossier de cache d'icônes (banners/eververse/)
ACCENT = 0x57C9E6  # cyan Poussière brillante

# Plafond de sécurité CV2 (cf. presenter Ada-1).
_MAX_ITEMS_PER_MESSAGE = 10


def _lines(item) -> list[str]:
    cost = f"{DUST_EMOJI} x{item.cost_quantity}" if item.cost_quantity is not None else ""
    return [f"**{item.name}**", getattr(item, "class_label", None) or "", cost]


async def _message(section: EververseSection, items: list, part: int, total: int, refresh_unix: int) -> Message:
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    header = f"# {TESS_EMOJI} {section.title}{suffix}\n{refresh_line(refresh_unix)}"
    message = Message(accent_color=ACCENT).add(text(header)).add(separator())

    any_item = False
    for index, item in enumerate(items):
        section_component = await item_section(item, _lines(item), f"ev_{index}.webp", FEATURE)
        if section_component is not None:
            message.add(section_component)
            any_item = True
    if not any_item:
        message.add(text("-# Aucun item pour cette rotation."))
    return message


async def build_post(sections: list[EververseSection]) -> Post:
    refresh_unix = int(next_reset().timestamp())
    messages: list[Message] = []
    for section in sections:
        chunks = list(chunked(section.items, _MAX_ITEMS_PER_MESSAGE)) or [[]]
        for part, chunk in enumerate(chunks):
            messages.append(await _message(section, list(chunk), part, len(chunks), refresh_unix))
    return Post(TOPIC, "repost", {"default": messages}, period_start=last_reset())
