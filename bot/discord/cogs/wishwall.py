# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds.wishwall import WishWallView, build_intro_embed
from bot.features import wishwall as feature


class WishWall(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wishes = feature.load_wishes()

    @app_commands.command(
        name="wish-wall",
        description="Affiche un embed interactif avec plusieurs vœux.",
    )
    async def wishwall(self, interaction: discord.Interaction):
        intro_image = feature.load_image(feature.DEFAULT_IMAGE)
        embed = build_intro_embed(intro_image)

        await interaction.response.send_message(
            embed=embed,
            view=WishWallView(self.wishes),
            files=feature.fresh_files(feature.DEFAULT_IMAGE),
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(WishWall(bot))