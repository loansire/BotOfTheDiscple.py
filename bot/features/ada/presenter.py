# -*- coding: utf-8 -*-
"""Calcul de la publication Ada-1 (Components V2).

Normalement UN message : titre + actualisation (prochain reset du mardi),
séparateur, puis une section par item (nom + coût Glimmer à gauche, icône
composée à droite). Les items s'enchaînent sans séparateur. Au-delà du
plafond CV2, le contenu est re-découpé avec un suffixe « (n/total) » ; la
ligne d'actualisation n'apparaît que sur le premier message.

Ada-1 étant un vendor PERMANENT : pas de message statut ni d'image d'en-tête."""
from __future__ import annotations

from bot.bungie.reset import TUESDAY, last_reset, next_weekday_reset
from bot.compute import item_section
from bot.content.model import Message, Post, separator, text
from bot.features.ada import TOPIC
from bot.features.ada.constants import ADA_EMOJI, ADA_LABEL, GLIMMER_EMOJI
from bot.features.ada.models import AdaItem
from bot.render.layout import chunked, refresh_line

FEATURE = "ada"  # sous-dossier de cache d'icônes (banners/ada/)
ACCENT = 0xC27C0E  # discord.Color.dark_gold()

# Plafond de sécurité CV2 (40 composants top-level/message). Un item coûte ~2
# composants (Section + Thumbnail). On garde de la marge sous 40 (container +
# titre + séparateur d'en-tête inclus).
_MAX_ITEMS_PER_MESSAGE = 9


def _lines(item: AdaItem) -> list[str]:
    cost = f"{GLIMMER_EMOJI} x{item.cost_quantity}" if item.cost_quantity is not None else ""
    return [f"**{item.name}**", cost]


async def _message(items: list[AdaItem], part: int, total: int, refresh_unix: int | None) -> Message:
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    header = f"# {ADA_EMOJI} {ADA_LABEL}{suffix}"
    if refresh_unix is not None:
        header += f"\n{refresh_line(refresh_unix)}"
    message = Message(accent_color=ACCENT).add(text(header)).add(separator())

    any_item = False
    for item in items:
        section = await item_section(item, _lines(item), f"ada_{item.item_hash}.webp", FEATURE)
        if section is not None:
            message.add(section)
            any_item = True
    if not any_item:
        message.add(text("-# Aucun item pour cette rotation."))
    return message


async def build_post(items: list[AdaItem]) -> Post:
    refresh_unix = int(next_weekday_reset(TUESDAY).timestamp())
    chunks = list(chunked(items, _MAX_ITEMS_PER_MESSAGE)) or [[]]
    messages = [
        await _message(list(chunk), part, len(chunks), refresh_unix if part == 0 else None)
        for part, chunk in enumerate(chunks)
    ]
    return Post(TOPIC, "repost", {"default": messages}, period_start=last_reset())
