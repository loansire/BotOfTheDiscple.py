# -*- coding: utf-8 -*-
"""Calcul des tables de butin (/loottable), rangées en base.

- topic `loot:<clé>` : une variante par page (`p1`, `p2`...). Chaque page :
  titre (emoji du type + libellé en majuscules + « (n/total) »), bannière de
  l'activité, une section par item (nom en lien light.gg + Souvenance, ligne
  « type • élément • munitions », note exotique ; icône composée), puis les
  boutons ◀ / ▶ (custom_id `loot:<clé>:<page>`, désactivés aux bornes).
- topic `loottable_index` : l'index de l'autocomplétion, une option par
  activité (libellé, clé, en-tête de son groupe déjà mis en forme), dans
  l'ordre d'affichage.

La commande et les boutons ne font que relire ces pages en base."""
from __future__ import annotations

from bot.compute import item_section, mime_of, read_resource
from bot.content.model import Component, Message, Post, button, image, text
from bot.features.loottable.constants import (
    ACTIVITY_BANNER_DIR,
    EXOTIC_NOTE,
    ICON_FEATURE,
    LIGHT_GG_BASE,
    MAX_ITEMS_PER_PAGE,
    SOUVENANCE_EMOJI,
    activity_type_label,
    activity_type_tag,
    ammo_type_tag,
    damage_type_tag,
    weapon_type_tag,
)
from bot.features.loottable.models import LootActivity, LootItem

ACCENT = 0x2E86AB
INDEX_TOPIC = "loottable_index"
_GROUP_WIDTH = 32


def topic_of(key: str) -> str:
    return f"loot:{key}"


def page_variant(page: int) -> str:
    """Variante d'une page (1 = première)."""
    return f"p{page}"


def page_action(key: str, page: int) -> str:
    return f"loot:{key}:{page}"


def group_header(activity_type: str | None) -> str:
    """En-tête d'un groupe dans l'autocomplétion : ═══ PRESTIGE ═══."""
    return f" {activity_type_label(activity_type).upper()} ".center(_GROUP_WIDTH, "═")[:100]


def _pages(items: list[LootItem]) -> list[list[LootItem]]:
    """Pages de MAX_ITEMS_PER_PAGE items, toujours au moins une."""
    if not items:
        return [[]]
    return [items[i:i + MAX_ITEMS_PER_PAGE] for i in range(0, len(items), MAX_ITEMS_PER_PAGE)]


def _lines(item: LootItem) -> list[str]:
    link = f"[**{item.name}**]({LIGHT_GG_BASE}{item.item_hash})"
    lines = [f"{link} {SOUVENANCE_EMOJI}" if item.craftable else link]
    tags = [t for t in (
        weapon_type_tag(item.sub_type, item.ammo_type),
        damage_type_tag(item.damage_type),
        ammo_type_tag(item.ammo_type),
    ) if t]
    if tags:
        lines.append("-# " + " • ".join(tags))
    if item.is_exotic:
        lines.append(EXOTIC_NOTE)
    return lines


async def _page(activity: LootActivity, items: list[LootItem], page: int, total: int) -> Message:
    emoji = activity_type_tag(activity.type)
    prefix = f"{emoji} " if emoji else ""
    suffix = "" if total == 1 else f" ({page}/{total})"
    message = Message(accent_color=ACCENT)
    message.add(text(f"## {prefix} Table de Loot - {activity.label.upper()}{suffix}"))

    if activity.banner:
        path = ACTIVITY_BANNER_DIR / activity.banner
        data = read_resource(path)
        if data is not None:
            message.add(image("gallery", data, path.name, mime=mime_of(path)))

    any_item = False
    for item in items:
        section = await item_section(item, _lines(item), f"loot_{item.item_hash}.webp", ICON_FEATURE)
        if section is not None:
            message.add(section)
            any_item = True
    if not any_item:
        message.add(text("-# *Aucun item à afficher.*"))

    if total > 1:
        message.add(button("◀", page_action(activity.key, page - 1), disabled=page == 1))
        message.add(button("▶", page_action(activity.key, page + 1), disabled=page == total))
    return message


async def build_post(activity: LootActivity) -> Post:
    pages = _pages(activity.items)
    variants = {
        page_variant(n): [await _page(activity, items, n, len(pages))]
        for n, items in enumerate(pages, start=1)
    }
    return Post(topic_of(activity.key), "on_demand", variants)


def build_index_post(activities: list[tuple[str, str, str | None]]) -> Post:
    """`activities` : (clé, libellé, type), déjà triés (cf. list_activities)."""
    message = Message()
    for key, label, activity_type in activities:
        message.add(Component("option", btn_label=label, btn_action=key, title=group_header(activity_type)))
    return Post(INDEX_TOPIC, "on_demand", {"default": [message]})
