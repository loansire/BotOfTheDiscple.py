# -*- coding: utf-8 -*-
import random

import discord

from bot.config import RESOURCES_DIR
from bot.embeds.builder import build_embed

MAINTENANCE_DIR = RESOURCES_DIR / "Maintenance"
FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"

ARTICLE_LINKS = {
    "destiny": "https://help.bungie.net/hc/en-us/articles/360049199271",
    "marathon": "https://help.marathonthegame.com/hc/en-us/articles/39001626488596",
}


class MaintenanceCopyView(discord.ui.View):
    def __init__(self, copy_text: str):
        super().__init__(timeout=None)
        self.copy_text = copy_text

    @discord.ui.button(label="Copier les infos", style=discord.ButtonStyle.primary, emoji="💾")
    async def copy_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"Voici le texte formaté, prêt à être copié:\n```\n{self.copy_text}\n```",
            ephemeral=True,
        )


def build_maintenance_embed(window: dict, copy_text: str | None = None):
    """Renvoie (embed, files NEUFS, view). Reconstruit les File à chaque appel."""
    game = window["game"]
    label = window["game_label"]
    off = window["offline_unix"]
    on = window.get("online_unix")
    link = ARTICLE_LINKS.get(game, "")

    fields = []
    if window.get("event_type"):
        fields.append({"name": "📝 __Commentaire(s)__", "value": window["event_type"], "inline": False})
    fields.append({"name": ":x: __Stop serveurs__", "value": f"<t:{off}:t>", "inline": True})
    if on:
        fields.append({"name": ":white_check_mark: __Retour serveurs__", "value": f"<t:{on}:t>", "inline": True})
    fields.append({"name": ":repeat: __Débute__", "value": f"**<t:{off}:R>**", "inline": False})

    files: list[discord.File] = []
    thumbnail_url = None
    n = random.randint(1, 11)
    thumb_path = MAINTENANCE_DIR / f"thumbnail_maintenance_{n}.png"
    if thumb_path.is_file():
        files.append(discord.File(thumb_path, filename="thumb.png"))
        thumbnail_url = "attachment://thumb.png"

    footer_icon_url = None
    if FOOTER_ICON_PATH.is_file():
        files.append(discord.File(FOOTER_ICON_PATH, filename="footer_icon.png"))
        footer_icon_url = "attachment://footer_icon.png"

    embed = build_embed(
        description=(
            f"## [Infos de Maintenance {label}]({link})\n"
            f"*Dernières informations concernant la maintenance de {label}.*\n"
        ),
        color=0xFF0000,
        thumbnail_url=thumbnail_url,
        fields=fields,
        footer_text="BotOfTheDisciple",
        footer_icon_url=footer_icon_url,
        add_date_to_footer=True,
    )

    view = MaintenanceCopyView(copy_text) if copy_text else None
    return embed, files, view