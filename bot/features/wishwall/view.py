# -*- coding: utf-8 -*-
import discord
from discord.ui import Select, View

from bot.render.embed import build_embed
from bot.features.wishwall import service as feature

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
            # custom_id STATIQUE : la vue est persistante (cf. WishWallView).
            custom_id="wishwall:select",
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
    """Vue PERSISTANTE : enregistrée au démarrage via bot.add_view() (cf.
    cogs/wishwall.py) pour que le menu des messages déjà postés reste
    utilisable après un redémarrage. Les vœux sont lus depuis le JSON au
    chargement du cog : l'index sélectionné reste valable tant que l'ordre de
    wishes.json ne change pas."""

    def __init__(self, wishes: list[dict]):
        super().__init__(timeout=None)
        self.add_item(WishSelect(wishes))