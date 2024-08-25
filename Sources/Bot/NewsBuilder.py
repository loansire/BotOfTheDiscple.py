from discord.ui import Button
import discord

from Sources.Bot.BungieNewsRequest import *

class ArticleLanguageView(View):
    def __init__(self, initial_article: dict, selected_language: str, is_both_language: bool, keyword: str):
        super().__init__(timeout=None)
        self.initial_article = initial_article
        self.selected_language = selected_language
        self.is_both_language = is_both_language
        self.keyword = keyword

        # Ajouter les boutons après l'initialisation de l'instance
        self.add_buttons()

    def add_buttons(self):
        # Déterminer le style des boutons
        if self.selected_language == 'en':
            english_style = discord.ButtonStyle.success
            french_style = discord.ButtonStyle.danger if not self.is_both_language else discord.ButtonStyle.secondary
        elif self.selected_language == 'fr' and self.is_both_language:
            english_style = discord.ButtonStyle.secondary
            french_style = discord.ButtonStyle.success
        else:
            english_style = discord.ButtonStyle.success
            french_style = discord.ButtonStyle.danger

        # Crée et ajoute le bouton anglais
        english_button = Button(
            label="EN",
            style=english_style,
            emoji="🇺🇸"
        )

        # Crée et ajoute le bouton Français
        french_button = Button(
            label="FR",
            style=french_style,
            emoji="🇫🇷",
            disabled=not self.is_both_language
        )

        # Associe les callbacks
        english_button.callback = self.english_button
        french_button.callback = self.french_button

        # Ajouter les boutons à la vue
        self.add_item(english_button)
        self.add_item(french_button)

        # Crée et ajoute le bouton Reload si applicable
        if not self.is_both_language:
            reload_button = Button(
                label=None,
                style=discord.ButtonStyle.secondary,
                emoji="🔄"
            )
            reload_button.callback = self.reload_button
            self.add_item(reload_button)

    async def update_embed(self, interaction: discord.Interaction, language: str):
        # Utilisation de la fonction générique avec le mot-clé
        article, is_both_language = await get_latest_article_by_keyword(language, self.keyword)

        if article:
            embed = discord.Embed(
                title=article.get('Title', 'Sans titre'),
                description=article.get('Description', 'Pas de description disponible'),
                url=f"https://www.bungie.net{article.get('Link', '#')}",
                color=discord.Color.dark_red()
            )
            embed.set_image(url=article.get('ImagePath', ''))
            embed.set_footer(text=f"{article.get('PubDate', 'Date inconnue')}")

            # Mettre à jour la langue et la disponibilité des langues
            self.selected_language = language
            self.is_both_language = is_both_language

            # Mettre à jour les boutons en fonction de la langue sélectionnée
            self.clear_items()
            self.add_buttons()

            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(content="Aucun article trouvé.", embed=None, view=self)

    async def english_button(self, interaction: discord.Interaction):
        await self.update_embed(interaction, 'en')

    async def french_button(self, interaction: discord.Interaction):
        await self.update_embed(interaction, 'fr')

    async def reload_button(self, interaction: discord.Interaction):
        # Obtenez les informations les plus récentes sur l'article pour la langue française
        article, is_both_language = await get_latest_article_by_keyword('fr', self.keyword)

        if not is_both_language:
            await interaction.response.send_message(
                content="⚠️ *La version Française de cet article n'a pas encore été publiée par Bungie.*",
                ephemeral=True
            )
        else:
            self.selected_language = 'fr'
            self.is_both_language = is_both_language
            await self.update_embed(interaction, 'fr')

async def news_article_command(interaction: discord.Interaction, language: str, keyword: str, no_article_message: str):
    # Utilisation de la fonction générique avec le mot-clé
    article, is_both_language = await get_latest_article_by_keyword(language=language, keyword=keyword)

    if article:
        embed = discord.Embed(
            title=article.get('Title', 'Sans titre'),
            description=article.get('Description', 'Pas de description disponible'),
            url=f"https://www.bungie.net{article.get('Link', '#')}",
            color=discord.Color.dark_red()
        )
        embed.set_image(url=article.get('ImagePath', ''))
        embed.set_footer(text=f"{article.get('PubDate', 'Date inconnue')}")

        # Initialiser la vue avec la langue sélectionnée et la disponibilité des langues
        view = ArticleLanguageView(article, language, is_both_language, keyword)

        # Si on demande la version française mais qu'elle n'existe pas encore
        if language == 'fr' and not is_both_language:
            await interaction.response.send_message(embed=embed, view=view)
            await interaction.followup.send(
                content="⚠️ *La version Française de cet article n'a pas encore été publiée par Bungie.*",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(no_article_message)
