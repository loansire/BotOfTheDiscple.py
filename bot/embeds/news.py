# -*- coding: utf-8 -*-
import discord
from discord.ui import Button, View

from bot.bungie.client import BUNGIE_BASE
from bot.config import RESOURCES_DIR
from bot.embeds.builder import build_embed
from bot.features.news import get_latest_article

FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"
_FR_UNAVAILABLE = "⚠️ *La version Française de cet article n'a pas encore été publiée par Bungie.*"


def _footer_files() -> list[discord.File]:
    if FOOTER_ICON_PATH.is_file():
        return [discord.File(FOOTER_ICON_PATH, filename="footer_icon.png")]
    return []


def build_news_embed(article: dict) -> discord.Embed:
    title = article.get("Title", "Sans titre")
    description = article.get("Description", "Pas de description disponible")
    url = f"{BUNGIE_BASE}{article.get('Link', '#')}"
    return build_embed(
        description=f"## [{title}]({url})\n{description}",
        color=discord.Color.dark_red(),
        image_url=article.get("ImagePath", ""),
        footer_text=article.get("PubDate", "Date inconnue"),
        footer_icon_url="attachment://footer_icon.png",
    )

def build_news_alert(
    article: dict, language: str, is_both_language: bool, keyword: str
) -> tuple[discord.Embed, list[discord.File], ArticleLanguageView]:
    """Adaptateur pour le publisher : renvoie (embed, files, view) NEUFS.
    (le publisher attend cet ordre ; build_article_message renvoie le warning en plus)."""
    embed, view, files, _ = build_article_message(article, language, is_both_language, keyword)
    return embed, files, view

class ArticleLanguageView(View):
    def __init__(self, language: str, is_both_language: bool, keyword: str):
        super().__init__(timeout=None)
        self.selected_language = language
        self.is_both_language = is_both_language
        self.keyword = keyword
        self._add_buttons()

    def _add_buttons(self):
        if self.selected_language == "en":
            en_style = discord.ButtonStyle.success
            fr_style = (
                discord.ButtonStyle.secondary
                if self.is_both_language
                else discord.ButtonStyle.danger
            )
        elif self.selected_language == "fr" and self.is_both_language:
            en_style = discord.ButtonStyle.secondary
            fr_style = discord.ButtonStyle.success
        else:
            en_style = discord.ButtonStyle.success
            fr_style = discord.ButtonStyle.danger

        en_btn = Button(label="EN", style=en_style, emoji="🇺🇸")
        fr_btn = Button(
            label="FR", style=fr_style, emoji="🇫🇷", disabled=not self.is_both_language
        )
        en_btn.callback = self._on_en
        fr_btn.callback = self._on_fr
        self.add_item(en_btn)
        self.add_item(fr_btn)

        if not self.is_both_language:
            reload_btn = Button(style=discord.ButtonStyle.secondary, emoji="🔄")
            reload_btn.callback = self._on_reload
            self.add_item(reload_btn)

    async def _refresh(self, interaction: discord.Interaction, language: str):
        article, is_both = await get_latest_article(language, self.keyword)
        if not article:
            await interaction.response.edit_message(
                content="Aucun article trouvé.", embed=None, view=self
            )
            return
        self.selected_language = language
        self.is_both_language = is_both
        self.clear_items()
        self._add_buttons()
        # Pas de re-attache de fichiers : l'attachment du 1er envoi persiste
        await interaction.response.edit_message(embed=build_news_embed(article), view=self)

    async def _on_en(self, interaction: discord.Interaction):
        await self._refresh(interaction, "en")

    async def _on_fr(self, interaction: discord.Interaction):
        await self._refresh(interaction, "fr")

    async def _on_reload(self, interaction: discord.Interaction):
        _, is_both = await get_latest_article("fr", self.keyword)
        if not is_both:
            await interaction.response.send_message(content=_FR_UNAVAILABLE, ephemeral=True)
        else:
            await self._refresh(interaction, "fr")


def build_article_message(
    article: dict, language: str, is_both_language: bool, keyword: str
) -> tuple[discord.Embed, ArticleLanguageView, list[discord.File], str | None]:
    """Assemble embed + vue + fichiers + message d'avertissement éventuel.
    Réutilisé par le cog News et par les alertes."""
    embed = build_news_embed(article)
    view = ArticleLanguageView(language, is_both_language, keyword)
    warning = _FR_UNAVAILABLE if (language == "fr" and not is_both_language) else None
    return embed, view, _footer_files(), warning