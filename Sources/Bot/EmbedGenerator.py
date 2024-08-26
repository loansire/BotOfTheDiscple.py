import discord
from datetime import datetime


def create_embed_with_components(description=None, color=discord.Color.default(), author=None,
                                 author_icon_url=None, thumbnail_url=None, image_url=None,
                                 fields=None, footer_text=None, footer_icon_url=None,
                                 add_date_to_footer=False, buttons=None, files=None):
    # Création de l'embed
    embed = discord.Embed(description=description, color=color)

    if author:
        embed.set_author(name=author, icon_url=author_icon_url)
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    if image_url:
        embed.set_image(url=image_url)
    if footer_text:
        if add_date_to_footer:
            footer_text += f" • {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)

    # Ajout des champs de manière dynamique
    if fields:
        for field in fields:
            embed.add_field(name=field['name'], value=field['value'], inline=field.get('inline', True))

    # Ajout des composants (boutons)
    components = []
    if buttons:
        action_row = discord.ui.ActionRow()
        for button in buttons:
            action_button = discord.ui.Button(label=button['label'], style=button['style'],
                                              custom_id=button['custom_id'], emoji=button.get('emoji'))
            action_row.add_item(action_button)
        components.append(action_row)

    return embed, components, files
