import discord
from datetime import datetime


def create_custom_embed(title=None, description=None, color=discord.Color.default(),
                        url=None, author=None, author_url=None, author_icon_url=None,
                        thumbnail_url=None, image_url=None, fields=None,
                        footer_text=None, footer_icon_url=None, add_date_to_footer=False):
    """
    Crée un embed Discord personnalisé.

    :param title: Titre de l'embed
    :param description: Description de l'embed
    :param color: Couleur de l'embed
    :param url: URL associée au titre de l'embed
    :param author: Nom de l'auteur
    :param author_url: URL de l'auteur
    :param author_icon_url: URL de l'icône de l'auteur
    :param thumbnail_url: URL de la miniature
    :param image_url: URL de l'image
    :param fields: Liste de champs, chaque champ est un dict avec 'name', 'value', et 'inline'
    :param footer_text: Texte du pied de page
    :param footer_icon_url: URL de l'icône du pied de page
    :param add_date_to_footer: Booléen pour ajouter ou non la date au footer
    :return: Un objet discord.Embed
    """
    embed = discord.Embed(title=title, description=description, color=color, url=url)

    if author:
        embed.set_author(name=author, url=author_url, icon_url=author_icon_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if image_url:
        embed.set_image(url=image_url)

    # Ajout du texte et de l'icône du pied de page, avec la date si nécessaire
    if footer_text:
        if add_date_to_footer:
            # Ajout de la date au format souhaité
            current_date = datetime.now().strftime('%Y-%m-%d')
            footer_text += f" • {current_date}"
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

    # Ajoute les champs de manière dynamique
    if fields:
        for field in fields:
            embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))

    return embed
