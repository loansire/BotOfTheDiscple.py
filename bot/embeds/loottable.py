# -*- coding: utf-8 -*-
"""Rendu Components V2 d'une table de butin (/loottable).

Un message PUBLIC, paginé si nécessaire. Structure d'une page :
- titre « <ACTIVITÉ> — LOOT TABLE » ;
- bannière locale pleine largeur (Ressources/ActivityBanner/<fichier>), si dispo ;
- une `ui.Section` par item, SANS séparateur entre elles (économie de composants) :
  à gauche le nom en lien light.gg (+ emoji Souvenance si façonnable) et la ligne
  de tags (type d'arme / élément / munitions), à droite l'icône composée
  (icon + watermark) en `ui.Thumbnail` ;
- une `ui.ActionRow` de pagination (◀ / compteur / ▶) uniquement si > 1 page.

Plafond de page : la contrainte DURE n'est pas les 40 composants CV2 mais les
10 PIÈCES JOINTES par message — 1 bannière + 1 icône par item → 9 items max
(MAX_ITEMS_PER_PAGE). Une page pleine coûte ~31 composants, on reste large.

La pagination édite le message en place (`edit_message`), en réémettant les
pièces jointes de la nouvelle page : un `discord.File` est consommé à l'envoi,
donc chaque page est reconstruite à neuf. Les icônes étant en cache disque
après le premier rendu, ce rebuild est quasi gratuit."""
from __future__ import annotations

from io import BytesIO

import discord
from discord import ui

from bot.embeds.xur_image import get_item_icon
from bot.features.loottable.constants import (
    ACTIVITY_BANNER_DIR,
    ICON_FEATURE,
    LIGHT_GG_BASE,
    MAX_ITEMS_PER_PAGE,
    SOUVENANCE_EMOJI,
    ammo_type_tag,
    damage_type_tag,
    weapon_type_tag, EXOTIC_NOTE, activity_type_tag,
)
from bot.features.loottable.models import LootActivity, LootItem
from bot.utils.logger import log

_ACCENT = discord.Color(0x2E86AB)

# Durée de vie des boutons de pagination (s). Passé ce délai ils sont
# désactivés : le message reste lisible, seule la navigation s'éteint.
_PAGINATION_TIMEOUT = 900


def _pages(items: list[LootItem]) -> list[list[LootItem]]:
    """Découpe les items en pages de MAX_ITEMS_PER_PAGE. Toujours >= 1 page
    (une liste vide donne une page vide, rendue comme « aucun item »)."""
    if not items:
        return [[]]
    return [
        items[i:i + MAX_ITEMS_PER_PAGE]
        for i in range(0, len(items), MAX_ITEMS_PER_PAGE)
    ]


def _name_line(item: LootItem) -> str:
    """Nom en lien light.gg, suivi de l'emoji Souvenance si façonnable."""
    link = f"[**{item.name}**]({LIGHT_GG_BASE}{item.item_hash})"
    return f"{link} {SOUVENANCE_EMOJI}" if item.craftable else link


def _tags_line(item: LootItem) -> str:
    """Ligne « type • élément • munitions ». Chaque tag est un emoji custom si
    renseigné, sinon son libellé FR. Les tags absents (item non-arme) sont
    simplement omis ; si aucun n'est disponible, renvoie une chaîne vide."""
    tags = [
        weapon_type_tag(item.sub_type, item.ammo_type),
        damage_type_tag(item.damage_type),
        ammo_type_tag(item.ammo_type),
    ]
    tags = [t for t in tags if t]
    return "-# " + " • ".join(tags) if tags else ""


async def _item_section(
    item: LootItem, files: list[discord.File]
) -> ui.Section | None:
    """Section d'un item. None si l'icône composée est indisponible (item ignoré)."""
    icon_bytes = await get_item_icon(
        item.item_hash, item.icon, item.watermark, feature=ICON_FEATURE
    )
    if icon_bytes is None:
        return None

    fname = f"loot_{item.item_hash}.webp"
    files.append(discord.File(BytesIO(icon_bytes), filename=fname))

    lines = [_name_line(item)]
    tags = _tags_line(item)
    if tags:
        lines.append(tags)
    if item.is_exotic:
        lines.append(EXOTIC_NOTE)

    return ui.Section(
        ui.TextDisplay("\n".join(lines)),
        accessory=ui.Thumbnail(f"attachment://{fname}"),
    )


def _banner_file(activity: LootActivity) -> discord.File | None:
    """Bannière locale de l'activité, ou None si non déclarée / introuvable."""
    if not activity.banner:
        return None
    path = ACTIVITY_BANNER_DIR / activity.banner
    if not path.is_file():
        return None
    return discord.File(path, filename=path.name)


class _PageButton(ui.Button):
    """Bouton de navigation : reconstruit intégralement la page cible."""

    def __init__(self, activity: LootActivity, target: int, label: str, disabled: bool):
        super().__init__(
            style=discord.ButtonStyle.secondary, label=label, disabled=disabled
        )
        self.activity = activity
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        try:
            view, files = await build_loot_page(self.activity, self.target)
        except Exception as e:
            log.error(f"[LootTable] Page {self.target} de « {self.activity.key} » : {e}")
            await interaction.response.send_message(
                "Impossible d'afficher cette page.", ephemeral=True
            )
            return
        await interaction.response.edit_message(view=view, attachments=files)
        view.message = interaction.message


class LootTableView(ui.LayoutView):
    """Vue d'une page de table de butin.

    `message` est renseigné après l'envoi pour permettre la désactivation des
    boutons à l'expiration du timeout."""

    def __init__(self, container: ui.Container, *, paginated: bool):
        super().__init__(timeout=_PAGINATION_TIMEOUT if paginated else None)
        self.message: discord.Message | None = None
        self.add_item(container)

    async def on_timeout(self):
        """Désactive la navigation sans toucher au contenu."""
        if self.message is None:
            return
        for child in self.walk_children():
            if isinstance(child, ui.Button):
                child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass


async def build_loot_page(
    activity: LootActivity, page: int = 0
) -> tuple[LootTableView, list[discord.File]]:
    """Construit (vue, fichiers NEUFS) pour une page donnée.

    `page` est borné aux pages existantes (aucune exception sur un index hors
    limites). Les fichiers renvoyés sont à usage unique : un `discord.File` est
    consommé à l'envoi, il faut donc rappeler cette fonction pour chaque
    (ré)affichage."""
    pages = _pages(activity.items)
    total = len(pages)
    page = max(0, min(page, total - 1))

    files: list[discord.File] = []
    container = ui.Container(accent_color=_ACCENT)

    emoji = activity_type_tag(activity.type)
    prefix = f"{emoji} " if emoji else ""
    suffix = "" if total == 1 else f" ({page + 1}/{total})"
    container.add_item(
        ui.TextDisplay(f"## {prefix} Table de Loot - {activity.label.upper()}{suffix}")
    )

    banner = _banner_file(activity)
    if banner is not None:
        files.append(banner)
        container.add_item(
            ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{banner.filename}"))
        )

    any_item = False
    for item in pages[page]:
        section = await _item_section(item, files)
        if section is None:
            continue
        container.add_item(section)
        any_item = True

    if not any_item:
        container.add_item(ui.TextDisplay("-# *Aucun item à afficher.*"))

    if total > 1:
        row = ui.ActionRow()
        row.add_item(_PageButton(activity, page - 1, "◀", page == 0))
        row.add_item(_PageButton(activity, page + 1, "▶", page == total - 1))
        container.add_item(row)

    return LootTableView(container, paginated=total > 1), files
