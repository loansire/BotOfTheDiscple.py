# -*- coding: utf-8 -*-
"""Cog /loottable : affiche la table de butin d'une activité.

Commande à la demande — aucun poll, aucun état persistant, aucun abonnement :
cette feature ne rentre pas dans la pipeline de reset (sa source est un fichier
maison, elle n'a ni cadence ni message à maintenir).

Politique de réponse : le defer est ÉPHÉMÈRE, donc tous les garde-fous
(séparateur sélectionné, activité inconnue, table vide, échec Bungie/rendu)
restent privés — ils éditent simplement le « thinking ». Le seul message
PUBLIC est le succès, envoyé en followup ; le placeholder éphémère est alors
supprimé pour ne rien laisser traîner.

L'autocomplétion relit le JSON à chaque frappe (fichier local, lecture
négligeable) : ajouter une activité ne demande donc pas de redémarrage.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds.loottable import build_loot_page
from bot.features.loottable import get_loot_table, list_activities
from bot.features.loottable.constants import activity_type_label
from bot.utils.logger import log

# Discord n'accepte que 25 suggestions d'autocomplétion par requête.
# Les séparateurs sont des Choice comme les autres : ils CONSOMMENT ce quota.
_MAX_CHOICES = 25

# Préfixe des `value` de séparateur. Un séparateur est sélectionnable (Discord
# ne sait pas rendre une entrée inerte) : la commande le rejette explicitement.
_SEPARATOR_PREFIX = "__sep__"

# Largeur de la ligne de séparation, en caractères.
_SEPARATOR_WIDTH = 32

# Sentinelle : « aucun groupe encore ouvert » (None est un type valide).
_UNSET = object()


def _separator_choice(activity_type: str | None) -> app_commands.Choice[str]:
    """Ligne d'en-tête d'un groupe : ═══ PRESTIGE ═══."""
    name = f" {activity_type_label(activity_type).upper()} ".center(
        _SEPARATOR_WIDTH, "═"
    )
    return app_commands.Choice(
        name=name[:100],
        value=f"{_SEPARATOR_PREFIX}{activity_type or 'inconnu'}",
    )


class LootTable(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Suggestions groupées par type d'activité, filtrées sur le libellé
        (insensible à la casse).

        `list_activities()` renvoie déjà les activités triées par type puis par
        libellé : il suffit de détecter les changements de type pour insérer un
        séparateur. Un séparateur n'est émis que s'il reste de la place pour
        LUI ET AU MOINS UNE activité (jamais de séparateur orphelin en fin de
        liste), et seulement si son groupe a au moins un résultat après filtre.

        `value` = clé interne (celle du JSON), `name` = libellé affiché."""
        needle = current.casefold()
        matches = [
            (key, label, atype)
            for key, label, atype in list_activities()
            if needle in label.casefold() or needle in key.casefold()
        ]

        choices: list[app_commands.Choice[str]] = []
        group: object = _UNSET
        for key, label, atype in matches:
            if atype != group:
                if len(choices) + 2 > _MAX_CHOICES:
                    break  # plus la place pour un groupe complet
                choices.append(_separator_choice(atype))
                group = atype
            if len(choices) >= _MAX_CHOICES:
                break
            choices.append(app_commands.Choice(name=label, value=key))
        return choices

    @staticmethod
    async def _fail(interaction: discord.Interaction, message: str) -> None:
        """Réponse d'échec : TOUJOURS éphémère.

        On édite le defer éphémère plutôt que d'envoyer un followup : un seul
        message privé, pas de « thinking » résiduel."""
        try:
            await interaction.edit_original_response(content=message)
        except discord.HTTPException as e:
            log.warning(f"[LootTable] Réponse d'erreur non délivrée : {e}")

    @app_commands.command(
        name="loottable",
        description="Affiche la table de butin d'une activité.",
    )
    @app_commands.describe(activite="Activité dont afficher la table de butin.")
    @app_commands.autocomplete(activite=_autocomplete)
    async def loottable(self, interaction: discord.Interaction, activite: str):
        # La résolution des items peut enchaîner plusieurs appels Bungie
        # (définitions non cachées) + des téléchargements d'icônes : on dépasse
        # facilement les 3 s d'ack. Defer ÉPHÉMÈRE : tant qu'on n'a pas un
        # rendu valide, rien ne doit apparaître publiquement.
        await interaction.response.defer(ephemeral=True)

        if activite.startswith(_SEPARATOR_PREFIX):
            await self._fail(
                interaction,
                "Cette ligne est un séparateur de catégorie, pas une activité.\n"
                "-# Choisis une activité listée en dessous.",
            )
            return

        try:
            activity = await get_loot_table(activite)
        except Exception as e:
            log.error(f"[LootTable] Résolution de « {activite} » échouée : {e}")
            await self._fail(
                interaction,
                "Impossible de récupérer cette table de butin pour l'instant.",
            )
            return

        if activity is None:
            await self._fail(
                interaction,
                f"Activité inconnue : `{activite}`.\n"
                "-# Utilise l'autocomplétion pour voir les activités disponibles.",
            )
            return

        if not activity.items:
            await self._fail(
                interaction,
                f"Aucun item déclaré pour **{activity.label}**.",
            )
            return

        try:
            view, files = await build_loot_page(activity, 0)
        except Exception as e:
            log.error(f"[LootTable] Rendu de « {activite} » échoué : {e}")
            await self._fail(
                interaction, "Impossible d'afficher cette table de butin."
            )
            return

        message = await interaction.followup.send(view=view, files=files, wait=True)
        # Référence nécessaire pour désactiver les boutons à l'expiration.
        view.message = message

        # Le résultat vit désormais dans le message public : on retire le
        # placeholder éphémère (best-effort, une erreur ici est sans impact).
        try:
            await interaction.delete_original_response()
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(LootTable(bot))