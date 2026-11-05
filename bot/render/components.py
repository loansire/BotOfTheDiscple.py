# -*- coding: utf-8 -*-
"""Rendu GÉNÉRIQUE d'un message stocké en base (bot/content/model.py) en
objets Discord. Aucun calcul : chaque Component devient un composant Discord,
dans l'ordre, avec les valeurs telles quelles.

Seule mécanique : les boutons consécutifs partagent une ActionRow (5 max),
et un `select` regroupe les `option` qui le suivent.

Une image stockée absente (base incomplète) n'empêche pas l'envoi : la
section retombe sur son texte seul, la galerie / vignette est omise.

Les boutons et menus ne portent qu'un custom_id : leur traitement au clic est
assuré par un gestionnaire global (pas par la vue), pour rester utilisable
après un redémarrage."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from io import BytesIO

import discord
from discord import ui

from bot.content.model import CV2, Component, Message
from bot.core.logger import log
from bot.render.emotes import resolve
from bot.render.layout import StaticView

_STYLES = {
    "primary": discord.ButtonStyle.primary,
    "secondary": discord.ButtonStyle.secondary,
    "success": discord.ButtonStyle.success,
    "danger": discord.ButtonStyle.danger,
}
_MAX_BUTTONS_PER_ROW = 5


@dataclass
class Rendered:
    view: ui.View | ui.LayoutView | None = None
    embed: discord.Embed | None = None
    files: list[discord.File] = field(default_factory=list)


def image_ids(message: Message) -> set[str]:
    return {c.image_id for c in message.components if c.image_id}


def _resolve_emotes(message: Message) -> Message:
    """Remplace les marqueurs `{e:clé}` par les emotes du bot courant
    (cf. bot/render/emotes.py). Le message stocké n'est pas modifié."""
    components = [
        replace(
            c,
            text=resolve(c.text),
            title=resolve(c.title),
            btn_label=resolve(c.btn_label),
            btn_emoji=resolve(c.btn_emoji) or None,
        )
        for c in message.components
    ]
    return replace(message, components=components)


def render(message: Message, images: dict[str, bytes]) -> Rendered:
    """`images` : id → octets (cf. bot/content/store.load_images). Renvoie des
    fichiers NEUFS à chaque appel (un discord.File est consommé à l'envoi)."""
    message = _resolve_emotes(message)
    files = _files(message, images)
    available = {c.image_name for c in message.components if c.image_id in images}
    if message.layout == CV2:
        return Rendered(view=_cv2(message, available), files=files)
    embed, view = _embed(message, available)
    return Rendered(view=view, embed=embed, files=files)


def _files(message: Message, images: dict[str, bytes]) -> list[discord.File]:
    files, seen = [], set()
    for c in message.components:
        if not c.image_id or c.image_name in seen:
            continue
        data = images.get(c.image_id)
        if data is None:
            log.warning(f"[Rendu] Image {c.image_id} ({c.image_name}) absente de la base.")
            continue
        seen.add(c.image_name)
        files.append(discord.File(BytesIO(data), filename=c.image_name))
    return files


def _source(c: Component, available: set[str]) -> str | None:
    """URL d'image du composant : pièce jointe stockée, sinon URL distante."""
    if c.image_id:
        return f"attachment://{c.image_name}" if c.image_name in available else None
    return c.image_url


# ── Interactifs (communs aux deux layouts) ──────────────────────────────


def _button(c: Component) -> ui.Button:
    if c.url:
        return ui.Button(label=c.btn_label, emoji=c.btn_emoji, url=c.url, disabled=bool(c.btn_disabled))
    return ui.Button(
        label=c.btn_label,
        emoji=c.btn_emoji,
        style=_STYLES.get(c.btn_style or "secondary", discord.ButtonStyle.secondary),
        custom_id=c.btn_action,
        disabled=bool(c.btn_disabled),
    )


def _interactive_rows(components: list[Component]) -> list[list[ui.Item]]:
    """Regroupe les boutons consécutifs (5 par ligne) ; un select et ses
    options forment une ligne à lui seul."""
    rows: list[list[ui.Item]] = []
    buttons: list[ui.Item] = []
    select: ui.Select | None = None

    def close_buttons():
        nonlocal buttons
        if buttons:
            rows.append(buttons)
            buttons = []

    for c in components:
        if c.kind == "button":
            select = None
            if len(buttons) == _MAX_BUTTONS_PER_ROW:
                close_buttons()
            buttons.append(_button(c))
        elif c.kind == "select":
            close_buttons()
            select = ui.Select(custom_id=c.btn_action, placeholder=c.title, disabled=bool(c.btn_disabled))
            rows.append([select])
        elif c.kind == "option" and select is not None:
            select.add_option(label=c.btn_label, value=c.btn_action, emoji=c.btn_emoji, description=c.text)
    close_buttons()
    return rows


_INTERACTIVE = {"button", "select", "option"}


# ── Components V2 ──────────────────────────────────────────────────────


def _cv2(message: Message, available: set[str]) -> ui.LayoutView:
    container = ui.Container(accent_color=message.accent_color)
    pending: list[Component] = []

    def flush_interactive():
        for row in _interactive_rows(pending):
            container.add_item(ui.ActionRow(*row))
        pending.clear()

    for c in message.components:
        if c.kind in _INTERACTIVE:
            pending.append(c)
            continue
        flush_interactive()
        if c.kind == "text":
            container.add_item(ui.TextDisplay(c.text or ""))
        elif c.kind == "separator":
            container.add_item(ui.Separator())
        elif c.kind == "section":
            src = _source(c, available)
            if src is None:
                container.add_item(ui.TextDisplay(c.text or ""))
            else:
                container.add_item(ui.Section(ui.TextDisplay(c.text or ""), accessory=ui.Thumbnail(src)))
        elif c.kind == "gallery":
            src = _source(c, available)
            if src is not None:
                container.add_item(ui.MediaGallery(discord.MediaGalleryItem(src)))
        else:
            log.warning(f"[Rendu] Composant « {c.kind} » ignoré dans un message Components V2.")
    flush_interactive()
    return StaticView(container)


# ── Embed ───────────────────────────────────────────────────────────────


def _embed(message: Message, available: set[str]) -> tuple[discord.Embed, ui.View | None]:
    embed = discord.Embed(color=message.accent_color)
    interactive: list[Component] = []
    for c in message.components:
        if c.kind in _INTERACTIVE:
            interactive.append(c)
        elif c.kind == "embed_author":
            embed.set_author(name=c.title or "", url=c.url, icon_url=_source(c, available))
        elif c.kind == "embed_description":
            embed.description = c.text
        elif c.kind == "embed_field":
            embed.add_field(name=c.title or "", value=c.text or "", inline=bool(c.inline_field))
        elif c.kind == "embed_thumbnail":
            embed.set_thumbnail(url=_source(c, available))
        elif c.kind == "embed_image":
            embed.set_image(url=_source(c, available))
        elif c.kind == "embed_footer":
            embed.set_footer(text=c.text, icon_url=_source(c, available))
        else:
            log.warning(f"[Rendu] Composant « {c.kind} » ignoré dans un embed.")

    if not interactive:
        return embed, None
    view = ui.View(timeout=None)
    for row in _interactive_rows(interactive):
        for item in row:
            view.add_item(item)
    return embed, view
