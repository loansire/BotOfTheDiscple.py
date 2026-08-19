# -*- coding: utf-8 -*-
"""Cog /loottable : affiche la table de butin d'une activité.

Commande PUBLIQUE et à la demande — aucun poll, aucun état persistant, aucun
abonnement : cette feature ne rentre pas dans la pipeline de reset (sa source
est un fichier maison, elle n'a ni cadence ni message à maintenir).

L'autocomplétion relit le JSON à chaque frappe (fichier local, lecture
négligeable) : ajouter une activité ne demande donc pas de redémarrage.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds.loottable import build_loot_page
from bot.features.loottable import get_loot_table, list_activities
from bot.utils.logger import log

# Discord n'accepte que 25 suggestions d'autocomplétion par requête.
_MAX_CHOICES = 25


class LootTable(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggestions d'activités, filtrées sur le libellé (insensible à la casse).

                L'ordre vient de `list_activities()` : type d'activité puis libellé.
                Les emojis custom ne sont pas rendus dans un `Choice.name` (texte brut
                côté Discord) — le type ne sert donc qu'au tri.

                `value` = clé interne (celle du JSON), `name` = libellé affiché."""
        needle = current.casefold()
        return [
            app_commands.Choice(name=label, value=key)
            for key, label, _ in list_activities()
            if needle in label.casefold() or needle in key.casefold()
        ][:_MAX_CHOICES]

    @app_commands.command(
        name="loottable",
        description="Affiche la table de butin d'une activité.",
    )
    @app_commands.describe(activite="Activité dont afficher la table de butin.")
    @app_commands.autocomplete(activite=_autocomplete)
    async def loottable(self, interaction: discord.Interaction, activite: str):
        # La résolution des items peut enchaîner plusieurs appels Bungie
        # (définitions non cachées) + des téléchargements d'icônes : on dépasse
        # facilement les 3 s d'ack. D'où le defer public.
        await interaction.response.defer()

        try:
            activity = await get_loot_table(activite)
        except Exception as e:
            log.error(f"[LootTable] Résolution de « {activite} » échouée : {e}")
            await interaction.followup.send(
                "Impossible de récupérer cette table de butin pour l'instant.",
                ephemeral=True,
            )
            return

        if activity is None:
            await interaction.followup.send(
                f"Activité inconnue : `{activite}`.\n"
                "-# Utilise l'autocomplétion pour voir les activités disponibles.",
                ephemeral=True,
            )
            return

        view, files = await build_loot_page(activity, 0)
        message = await interaction.followup.send(view=view, files=files, wait=True)
        # Référence nécessaire pour désactiver les boutons à l'expiration.
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(LootTable(bot))
