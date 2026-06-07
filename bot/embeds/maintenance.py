# -*- coding: utf-8 -*-
import random

import discord

from bot.config import RESOURCES_DIR
from bot.embeds.builder import build_embed
from bot.features.maintenance.fetcher import ARTICLES
from bot.features.maintenance.models import resolve_game

MAINTENANCE_DIR = RESOURCES_DIR / "Maintenance"
FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"

# Métadonnées d'affichage par jeu
GAME_META = {
    "destiny": {
        "article_locale": "en-us",
        "author_name": "@help.bungie.net",
        "author_url": "https://help.bungie.net",
        "emoji_id": "710283624619966484",
        "thumb_dir": "Destiny2",
        "thumb_count": 11,
    },
    "marathon": {
        "article_locale": "en-us",
        "author_name": "@help.marathonthegame",
        "author_url": "https://help.marathonthegame.com",
        "emoji_id": "1111270580923142164",
        "thumb_dir": "Marathon",
        "thumb_count": 1,
    },
}


def _article_link(game: str) -> str:
    """Reconstruit l'URL publique de l'article depuis l'id défini dans fetcher."""
    cfg = ARTICLES[resolve_game(game)]
    locale = GAME_META[game]["article_locale"]
    return f"{cfg['base_url']}/hc/{locale}/articles/{cfg['article_id']}"


def _emoji_icon_url(game: str) -> str:
    """URL CDN de l'emoji custom du jeu (cas A : aucune image locale)."""
    return f"https://cdn.discordapp.com/emojis/{GAME_META[game]['emoji_id']}.png"


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
    meta = GAME_META.get(game, {})
    link = _article_link(game) if meta else ""

    fields = []
    if window.get("event_type"):
        fields.append({"name": "📝 __Commentaire(s)__", "value": window["event_type"], "inline": False})
    fields.append({"name": ":x: __Stop serveurs__", "value": f"<t:{off}:t>", "inline": True})
    if on:
        fields.append({"name": ":white_check_mark: __Retour serveurs__", "value": f"<t:{on}:t>", "inline": True})
    fields.append({"name": ":repeat: __Débute__", "value": f"**<t:{off}:R>**", "inline": False})

    files: list[discord.File] = []

    # Thumbnail : dossier + nombre de visuels propres au jeu
    thumbnail_url = None
    if meta:
        n = random.randint(1, meta["thumb_count"])
        thumb_path = MAINTENANCE_DIR / meta["thumb_dir"] / f"thumbnail_maintenance_{n}.png"
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
        author=meta.get("author_name"),
        author_url=meta.get("author_url"),
        author_icon_url=_emoji_icon_url(game) if meta else None,
        thumbnail_url=thumbnail_url,
        fields=fields,
        footer_text="BotOfTheDisciple",
        footer_icon_url=footer_icon_url,
        add_date_to_footer=True,
    )

    view = MaintenanceCopyView(copy_text) if copy_text else None
    return embed, files, view