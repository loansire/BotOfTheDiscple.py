# -*- coding: utf-8 -*-
from collections import Counter
from datetime import datetime

import discord

from bot.config import RESOURCES_DIR

FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"


def build_randomizer_embed(
    *,
    chosen: str,
    counts: Counter,
    data: dict,
    title: str,
    item_type: str,
) -> tuple[discord.Embed, list[discord.File]]:
    """Construit l'embed du tirage + la liste des fichiers à attacher."""
    embed = discord.Embed(
        title=f"{title} Aléatoire Sélectionné",
        colour=0xFFAE00,
        timestamp=datetime.now(),
    )

    item_text = "\n".join(
        f"> {data[item]['emoji']} {item} (x{n})" for item, n in counts.items()
    )
    embed.add_field(name=f"Liste des {item_type} choisis", value=item_text, inline=True)
    embed.add_field(name=f"{item_type} tiré au sort", value=chosen, inline=False)

    files: list[discord.File] = []
    prefix = item_type.lower()

    image_path = data[chosen].get("image")
    if image_path and (RESOURCES_DIR.parent / image_path).is_file():
        f = discord.File(image_path, filename=f"{prefix}_image.png")
        files.append(f)
        embed.set_image(url=f"attachment://{prefix}_image.png")

    thumb_path = data[chosen].get("thumbnail")
    if thumb_path and (RESOURCES_DIR.parent / thumb_path).is_file():
        f = discord.File(thumb_path, filename=f"{prefix}_thumbnail.png")
        files.append(f)
        embed.set_thumbnail(url=f"attachment://{prefix}_thumbnail.png")

    if FOOTER_ICON_PATH.is_file():
        files.append(discord.File(FOOTER_ICON_PATH, filename="footer_icon.png"))
        embed.set_footer(text="BotOfTheDisciple", icon_url="attachment://footer_icon.png")

    return embed, files