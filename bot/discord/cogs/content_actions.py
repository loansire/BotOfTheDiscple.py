# -*- coding: utf-8 -*-
"""Clics sur les boutons des publications stockées en base.

Les messages rendus depuis la base (bot/render/components.py) ne portent que
des custom_id ; ce cog les traite en relisant la base, ce qui marche aussi
après un redémarrage et sur un bot qui ne fait que publier :
- `maintenance:copy:<jeu>` : texte prêt à copier de la maintenance en cours ;
- `news:<topic>:en|fr|check` : bascule de langue d'une news (check = la
  version FR est-elle publiée ?) ;
- `loot:<clé>:<page>` : pagination d'une table de butin ;
- `wishwall:select` : vœu choisi dans le menu du Wishwall ;
- `weekly:rota:raid|dungeon` : rotation prédictive (réponse éphémère).

Point d'entrée UNIQUE de ces custom_id : aucune vue persistante ne doit les
déclarer. discord.py mémorise la vue de chaque message envoyé et la consulte
AVANT les vues persistantes ; les boutons rendus depuis la base n'ayant pas
d'action propre, une vue persistante du même custom_id ne serait jamais
appelée (« n'a pas répondu à temps »)."""
import discord
from discord.ext import commands

from bot.core.logger import log
from bot.features.loottable.presenter import page_variant
from bot.features.loottable.presenter import topic_of as loot_topic
from bot.features.maintenance.presenter import COPY, topic_of
from bot.features.news.presenter import CHECK, EN, FR
from bot.features.wishwall.presenter import SELECT_ID
from bot.features.wishwall.presenter import TOPIC as WISHWALL_TOPIC
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
            elif custom_id.startswith("loot:"):
                _, key, page = custom_id.split(":", 2)
                await self._replace(interaction, loot_topic(key), page_variant(int(page)))
            elif custom_id == SELECT_ID:
                choice = ((interaction.data or {}).get("values") or [""])[0]
                await self._replace(interaction, WISHWALL_TOPIC, choice)
            elif custom_id.startswith("weekly:rota:"):
                await self._rotation(interaction, custom_id.rsplit(":", 1)[1])
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

    @staticmethod
    async def _rotation(interaction: discord.Interaction, kind: str) -> None:
        """Rotation prédictive précalculée (bot/features/weekly/handler.py),
        envoyée en éphémère. Le defer éphémère rend aussi l'erreur privée."""
        await interaction.response.defer(ephemeral=True, thinking=True)
        snap = await snapshot(f"rotation_{kind}")
        if snap is None:
            await interaction.followup.send(
                "⚠️ La rotation de la semaine n'est pas encore disponible. "
                "Réessaie dans quelques minutes.",
                ephemeral=True,
            )
            return
        out = snap.render()
        await interaction.followup.send(view=out.view, files=out.files, ephemeral=True)

    @staticmethod
    async def _replace(interaction: discord.Interaction, topic: str, variant: str) -> None:
        """Remplace le message par une autre variante (page, vœu), pièces
        jointes comprises."""
        snap = await snapshot(topic, variant)
        if snap is None:
            await interaction.response.send_message("Impossible d'afficher cette page.", ephemeral=True)
            return
        out = snap.render()
        if out.embed is not None:
            await interaction.response.edit_message(embed=out.embed, view=out.view, attachments=out.files)
        else:
            await interaction.response.edit_message(view=out.view, attachments=out.files)


async def setup(bot: commands.Bot):
    await bot.add_cog(ContentActions(bot))
