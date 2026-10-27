# -*- coding: utf-8 -*-
from datetime import datetime

import discord


def build_embed(
    *,
    description: str | None = None,
    color: int | discord.Color = discord.Color.dark_red(),
    author: str | None = None,
    author_url: str | None = None,
    author_icon_url: str | None = None,
    thumbnail_url: str | None = None,
    image_url: str | None = None,
    fields: list[dict] | None = None,
    footer_text: str | None = None,
    footer_icon_url: str | None = None,
    add_date_to_footer: bool = False,
) -> discord.Embed:
    embed = discord.Embed(description=description, color=color)

    if author:
        embed.set_author(name=author, url=author_url, icon_url=author_icon_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if image_url:
        embed.set_image(url=image_url)

    if fields:
        for field in fields:
            embed.add_field(
                name=field["name"],
                value=field["value"],
                inline=field.get("inline", True),
            )

    if footer_text:
        if add_date_to_footer:
            footer_text += f" • {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    elif add_date_to_footer:
        embed.set_footer(text=datetime.now().strftime("%Y/%m/%d %H:%M"))

    return embed