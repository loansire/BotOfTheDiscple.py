# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds.news import build_article_message
from bot.features import news as feature

_LANG_CHOICES = [
    app_commands.Choice(name="En", value="en"),
    app_commands.Choice(name="Fr", value="fr"),
]


class News(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_article(
        self, interaction: discord.Interaction, language: str, keyword: str, not_found: str
    ):
        article, is_both = await feature.get_latest_article(language, keyword)
        if not article:
            await interaction.response.send_message(not_found, ephemeral=True)
            return

        embed, view, files, warning = build_article_message(article, language, is_both, keyword)
        await interaction.response.send_message(embed=embed, view=view, files=files)
        if warning:
            await interaction.followup.send(content=warning, ephemeral=True)

    @app_commands.command(name="twid", description="Affiche la TWID la plus récente.")
    @app_commands.describe(language="Langue de l'article")
    @app_commands.choices(language=_LANG_CHOICES)
    async def twid(self, interaction: discord.Interaction, language: str):
        await self._send_article(interaction, language, "twid", "Aucun article TWID/TWAB trouvé.")

    @app_commands.command(
        name="twab", description="Affiche la TWAB la plus récente. Rien que pour Nexus o7"
    )
    @app_commands.describe(language="Langue de l'article")
    @app_commands.choices(language=_LANG_CHOICES)
    async def twab(self, interaction: discord.Interaction, language: str):
        # Volontairement identique à /twid (Bungie regroupe TWID/TWAB)
        await self._send_article(interaction, language, "twid", "Aucun article TWID/TWAB trouvé.")

    @app_commands.command(name="patch-note", description="Affiche le dernier patch note Destiny 2.")
    @app_commands.describe(language="Langue de l'article")
    @app_commands.choices(language=_LANG_CHOICES)
    async def patch_note(self, interaction: discord.Interaction, language: str):
        await self._send_article(
            interaction, language, "destiny_update", "Aucun article de patch note trouvé."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(News(bot))