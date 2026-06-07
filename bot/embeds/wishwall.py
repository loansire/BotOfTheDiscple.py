# -*- coding: utf-8 -*-
import discord
from discord.ui import Select, View

from bot.embeds.builder import build_embed
from bot.features import wishwall as feature

_COLOR = 0x6E00F5


def build_wish_embed(wish: dict, image: discord.File) -> discord.Embed:
    return build_embed(
        description="## " + wish["nom"] + "\n" + wish["description"],
        color=_COLOR,
        image_url=f"attachment://{image.filename}",
        thumbnail_url="attachment://thumbnail.png",
        footer_text="BotOfTheDisciple",
        footer_icon_url="attachment://footer_icon.png",
    )


def build_intro_embed(image: discord.File) -> discord.Embed:
    return build_embed(
        description="## Wishwall\nSélectionnez un vœu dans le menu déroulant pour voir les détails.",
        color=_COLOR,
        image_url=f"attachment://{image.filename}",
        thumbnail_url="attachment://thumbnail.png",
        footer_text="BotOfTheDisciple",
        footer_icon_url="attachment://footer_icon.png",
    )


class WishSelect(Select):
    def __init__(self, wishes: list[dict]):
        options = [
            discord.SelectOption(
                label=wish.get("BoutonName", wish["nom"].split(" - ")[-1]),
                value=str(i),
            )
            for i, wish in enumerate(wishes)
        ]
        super().__init__(
            placeholder="Sélectionnez un vœu...",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.wishes = wishes

    async def callback(self, interaction: discord.Interaction):
        wish = self.wishes[int(self.values[0])]

        # Image servant à référencer attachment:// (filename réel après fallback)
        ref_image = feature.load_image(wish["image"])
        embed = build_wish_embed(wish, ref_image)

        await interaction.response.edit_message(
            embed=embed,
            attachments=feature.fresh_files(wish["image"]),
        )


class WishWallView(View):
    def __init__(self, wishes: list[dict]):
        super().__init__(timeout=None)
        self.add_item(WishSelect(wishes))