# -*- coding: utf-8 -*-
"""Cog /wish-wall : embed interactif des vœux de la Dernière Volonté.

Calcul (bot live) : le Wishwall est recalculé toutes les 10 minutes (les vœux
sont édités à la main en base) et rangé en base. La commande et le menu de
sélection (cf. bot/discord/cogs/content_actions.py) relisent la base."""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.compute import store
from bot.core.logger import log
from bot.features.wishwall.presenter import INTRO, TOPIC, build_post
from bot.publishing.content_source import snapshot


class WishWall(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.refresh_content.start()

    def cog_unload(self):
        self.refresh_content.cancel()

    @tasks.loop(minutes=10)
    async def refresh_content(self):
        try:
            await store(build_post(), "WishWall")
        except Exception as e:
            log.error(f"[WishWall] Calcul échoué : {e}")

    @app_commands.command(
        name="wish-wall",
        description="Affiche un embed interactif avec plusieurs vœux.",
    )
    async def wishwall(self, interaction: discord.Interaction):
        snap = await snapshot(TOPIC, INTRO)
        if snap is None:
            await interaction.response.send_message(":x: Wishwall indisponible pour l'instant.", ephemeral=True)
            return
        out = snap.render()
        await interaction.response.send_message(embed=out.embed, view=out.view, files=out.files)


async def setup(bot: commands.Bot):
    await bot.add_cog(WishWall(bot))
