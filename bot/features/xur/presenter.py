# -*- coding: utf-8 -*-
"""Calcul des publications Xûr (Components V2).

- topic `xur_status` : le message statut, en deux variantes rangées ensemble
  (`present` : « Xûr est là » + date de départ ; `absent` : « Xûr n'est pas
  là » + date de retour). Le handler choisit la variante, sans calcul.
- topic `xur` : les messages catégories (un par vendor non vide, re-découpé
  au-delà du plafond CV2) : titre, image d'en-tête du vendor (largeIcon),
  puis une section par item (nom + Souvenance, détail arme / armure, perks
  col 3-4 avec liens d2glossary, coût en Pièces étranges ; icône composée)."""
from __future__ import annotations

from bot.bungie.reset import last_reset
from bot.compute import item_section
from bot.content.model import Message, Post, image, text
from bot.features.vanguard.constants import ARMOR_SUBTYPE_LABELS
from bot.features.vanguard.presenter import armor_lines, weapon_tags
from bot.features.xur import next_arrival_unix, next_departure_unix
from bot.features.xur.models import XurVendor
from bot.features.xur.state import TOPIC
from bot.render.item_icon import get_vendor_icon
from bot.render.layout import chunked
from bot.render.emotes import e

STATUS_TOPIC = "xur_status"
PRESENT, ABSENT = "present", "absent"
FEATURE = "xur"  # sous-dossier de cache d'icônes (banners/xur/)

ACCENT = 0xF1C40F  # discord.Color.gold()
_TITLE = e("topic.xur")  # emoji custom Xûr
_PIECES_EMOJI = e("currency.strange_coins")
SOUVENANCE_EMOJI = e("misc.craftable")
_D2GLOSSARY_PERK = "https://d2glossary.fr/perk.html?id="

# Plafond CV2 : 40 composants top-level par message ; un item coûte ~2
# composants. Limite de sécurité par message catégorie.
_MAX_ITEMS_PER_MESSAGE = 9


# ── Statut (présent / absent) ──────────────────────────────────────────


def build_status_post() -> Post:
    departure, arrival = next_departure_unix(), next_arrival_unix()
    present = (
        f"# {_TITLE} XÛR EST LÀ\n"
        f"Xûr disparaîtra le <t:{departure}:F> (<t:{departure}:R>)"
    )
    absent = (
        f"# {_TITLE} XÛR N'EST PAS LÀ\n"
        f"Xûr revient le <t:{arrival}:F> (<t:{arrival}:R>)"
    )
    return Post(STATUS_TOPIC, "edit", {
        PRESENT: [Message(accent_color=ACCENT).add(text(present))],
        ABSENT: [Message(accent_color=ACCENT).add(text(absent))],
    }, period_start=last_reset())


# ── Catégories ──────────────────────────────────────────────────────────


def _cost_line(item) -> str:
    return f"{_PIECES_EMOJI} x{item.cost_quantity}" if item.cost_quantity is not None else ""


def _perks_line(item) -> str:
    """'[nom](<url>) • [nom](<url>)' ; les chevrons suppriment l'aperçu de lien."""
    perks = getattr(item, "perks", None) or []
    return " • ".join(f"[{p.name}](<{_D2GLOSSARY_PERK}{p.plug_hash}>)" for p in perks)


def _detail_lines(item) -> list[str]:
    """Type / élément / munitions d'une arme, ou pièce + set d'armure."""
    if item.sub_type in ARMOR_SUBTYPE_LABELS:
        return armor_lines(item)
    tags = weapon_tags(item) if item.sub_type is not None else ""
    return [tags] if tags else []


def _name_line(item) -> str:
    if getattr(item, "craftable", False):
        return f"**{item.name}** {SOUVENANCE_EMOJI}"
    return f"**{item.name}**"


async def _vendor_message(vendor: XurVendor, items: list, part: int, total: int) -> Message | None:
    suffix = "" if total == 1 else f" ({part + 1}/{total})"
    message = Message(accent_color=ACCENT).add(text(f"## {vendor.emoji} {vendor.label}{suffix}"))
    if vendor.large_icon:
        fetched = await get_vendor_icon(vendor.key, vendor.large_icon)
        if fetched is not None:
            data, fname = fetched
            message.add(image("gallery", data, fname))

    any_item = False
    for item in items:
        lines = [_name_line(item), *_detail_lines(item), _perks_line(item), _cost_line(item)]
        section = await item_section(item, lines, f"xur_{vendor.key}_{item.item_hash}.webp", FEATURE)
        if section is not None:
            message.add(section)
            any_item = True
    return message if any_item else None  # aucun item résoluble → pas de message


async def build_post(vendors: list[XurVendor]) -> Post:
    messages: list[Message] = []
    for vendor in vendors:
        if not vendor.items:
            continue
        chunks = list(chunked(vendor.items, _MAX_ITEMS_PER_MESSAGE))
        for part, chunk in enumerate(chunks):
            message = await _vendor_message(vendor, list(chunk), part, len(chunks))
            if message is not None:
                messages.append(message)
    return Post(TOPIC, "repost", {"default": messages}, period_start=last_reset())
