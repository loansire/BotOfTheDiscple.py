# -*- coding: utf-8 -*-
"""Cog /loottable : affiche la table de butin d'une activité.

Calcul (bot live) : toutes les tables sont calculées au démarrage puis toutes
les REFRESH_HOURS heures et rangées en base (cf.
bot/features/loottable/presenter.py), avec l'index de l'autocomplétion.
Publication : la commande, l'autocomplétion et les boutons ◀ / ▶ (cf.
bot/discord/cogs/content_actions.py) ne font que relire la base.

Politique de réponse : le defer est PUBLIC, car c'est la réponse INITIALE qui
fixe l'éphémérité de TOUTE l'interaction — un defer éphémère rendrait aussi le
message de succès privé. Les garde-fous instantanés (séparateur sélectionné,
activité inconnue) sont donc contrôlés AVANT tout defer et répondent en
éphémère direct ; les erreurs tardives suppriment le placeholder « thinking »
public puis envoient un followup éphémère.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.compute import store
from bot.content import store as content_store
from bot.core.logger import log
from bot.features.loottable import get_loot_table, list_activities
from bot.features.loottable.presenter import (
    INDEX_TOPIC,
    build_index_post,
    build_post,
    page_variant,
    topic_of,
)
from bot.publishing.content_source import snapshot

_MAX_CHOICES = 25
_SEPARATOR_PREFIX = "__sep__"
REFRESH_HOURS = 6


async def produce_all() -> None:
    """Calcule toutes les tables de butin + l'index, et les range en base.
    Une activité en échec n'empêche pas les autres."""
    activities = list_activities()
    for key, _, _ in activities:
        try:
            activity = await get_loot_table(key)
        except Exception as e:
            log.warning(f"[LootTable] Calcul de « {key} » échoué : {e}")
            continue
        if activity is not None and activity.items:
            await store(await build_post(activity), "LootTable")
    await store(build_index_post(activities), "LootTable")


async def _index() -> list:
    """Options de l'index : (clé, libellé, en-tête de groupe), dans l'ordre."""
    post = await content_store.load_post(INDEX_TOPIC)
    if post is None or not post.messages:
        return []
    return [(c.btn_action, c.btn_label, c.title) for c in post.messages[0].components]


class LootTable(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.refresh_content.start()

    def cog_unload(self):
        self.refresh_content.cancel()

    @tasks.loop(hours=REFRESH_HOURS)
    async def refresh_content(self):
        try:
            await produce_all()
        except Exception as e:
            log.error(f"[LootTable] Calcul des tables échoué : {e}")

    @refresh_content.before_loop
    async def _before_refresh(self):
        await self.bot.wait_until_ready()

    async def _autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggestions groupées par type d'activité, filtrées sur le libellé ou
        la clé (insensible à la casse). Un en-tête de groupe n'est émis que
        s'il reste de la place pour LUI ET AU MOINS UNE activité."""
        needle = current.casefold()
        choices: list[app_commands.Choice[str]] = []
        group = None
        for key, label, header in await _index():
            if needle not in label.casefold() and needle not in key.casefold():
                continue
            if header != group:
                if len(choices) + 2 > _MAX_CHOICES:
                    break  # plus la place pour un groupe complet
                choices.append(app_commands.Choice(name=header, value=f"{_SEPARATOR_PREFIX}{header}"[:100]))
                group = header
            if len(choices) >= _MAX_CHOICES:
                break
            choices.append(app_commands.Choice(name=label, value=key))
        return choices

    @staticmethod
    async def _fail_early(interaction: discord.Interaction, message: str) -> None:
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException as e:
            log.warning(f"[LootTable] Réponse d'erreur non délivrée : {e}")

    @staticmethod
    async def _fail_late(interaction: discord.Interaction, message: str) -> None:
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass
        try:
            await interaction.followup.send(message, ephemeral=True)
        except discord.HTTPException as e:
            log.warning(f"[LootTable] Réponse d'erreur non délivrée : {e}")

    @app_commands.command(
        name="loottable",
        description="Affiche la table de butin d'une activité.",
    )
    @app_commands.describe(activite="Activité dont afficher la table de butin.")
    @app_commands.autocomplete(activite=_autocomplete)
    async def loottable(self, interaction: discord.Interaction, activite: str):
        if activite.startswith(_SEPARATOR_PREFIX):
            await self._fail_early(
                interaction,
                "Cette ligne est un séparateur de catégorie, pas une activité.\n"
                "-# Choisis une activité listée en dessous.",
            )
            return
        if activite not in {key for key, _, _ in await _index()}:
            await self._fail_early(
                interaction,
                f"Activité inconnue : `{activite}`.\n"
                "-# Utilise l'autocomplétion pour voir les activités disponibles.",
            )
            return

        await interaction.response.defer()
        try:
            snap = await snapshot(topic_of(activite), page_variant(1))
        except Exception as e:
            log.error(f"[LootTable] Lecture de « {activite} » échouée : {e}")
            await self._fail_late(interaction, "Impossible de récupérer cette table de butin pour l'instant.")
            return
        if snap is None:
            await self._fail_late(interaction, f"Aucun item à afficher pour `{activite}`.")
            return
        out = snap.render()
        await interaction.followup.send(view=out.view, files=out.files)


async def setup(bot: commands.Bot):
    await bot.add_cog(LootTable(bot))
