# -*- coding: utf-8 -*-
"""Clics sur les boutons des publications stockées en base.

Les messages rendus depuis la base (bot/render/components.py) ne portent que
des custom_id ; ce cog les traite en relisant la base, ce qui marche aussi
après un redémarrage et sur un bot qui ne fait que publier :
- `maintenance:copy:<jeu>` : texte prêt à copier de la maintenance en cours ;
- `news:<topic>:en|fr|check` : bascule de langue d'une news (check = la
  version FR est-elle publiée ?).

Les boutons gérés par une vue persistante (rotation prédictive, wishwall,
/botconfig) ne passent pas par ici."""
import discord
from discord.ext import commands

from bot.core.logger import log
from bot.features.maintenance.presenter import COPY, topic_of
from bot.features.news.presenter import CHECK, EN, FR
from bot.publishing.content_source import snapshot

_FR_UNAVAILABLE = "⚠️ *La version Française de cet article n'a pas encore été publiée par Bungie.*"


class ContentActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = (interaction.data or {}).get("custom_id", "")
        try:
            if custom_id.startswith("maintenance:copy:"):
                await self._maintenance_copy(interaction, custom_id.split(":", 2)[2])
            elif custom_id.startswith("news:"):
                _, topic, what = custom_id.split(":", 2)
                await self._news(interaction, topic, what)
        except Exception as e:
            log.error(f"[Boutons] {custom_id} : {e}")

    async def _maintenance_copy(self, interaction: discord.Interaction, game: str) -> None:
        snap = await snapshot(topic_of(game), COPY)
        if snap is None:
            await interaction.response.send_message(":x: Aucune maintenance enregistrée.", ephemeral=True)
            return
        copy_text = snap.messages[0].components[0].text
        await interaction.response.send_message(
            f"Voici le texte formaté, prêt à être copié:\n```\n{copy_text}\n```", ephemeral=True
        )

    async def _news(self, interaction: discord.Interaction, topic: str, what: str) -> None:
        language = FR if what == CHECK else what
        if language not in (EN, FR):
            return
        snap = await snapshot(topic, language)
        if snap is None:
            if language == FR:
                await interaction.response.send_message(_FR_UNAVAILABLE, ephemeral=True)
            else:
                await interaction.response.send_message("Aucun article trouvé.", ephemeral=True)
            return
        out = snap.render()
        # Pas de re-attache de fichiers : l'icône du pied de page du 1er envoi
        # (même nom de pièce jointe) reste en place.
        await interaction.response.edit_message(embed=out.embed, view=out.view)


async def setup(bot: commands.Bot):
    await bot.add_cog(ContentActions(bot))
