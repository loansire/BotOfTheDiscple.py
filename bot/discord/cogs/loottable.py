# -*- coding: utf-8 -*-
"""Cog /loottable : affiche la table de butin d'une activité.

Commande à la demande — aucun poll, aucun état persistant, aucun abonnement :
cette feature ne rentre pas dans la pipeline de reset (sa source est un fichier
maison, elle n'a ni cadence ni message à maintenir).

Politique de réponse : le defer est PUBLIC, car c'est la réponse INITIALE qui
fixe l'éphémérité de TOUTE l'interaction — un defer éphémère rendrait aussi le
message de succès privé, `ephemeral=False` sur le followup n'y changeant rien.
Conséquence : les garde-fous instantanés (séparateur sélectionné, activité
inconnue) sont contrôlés AVANT tout defer et répondent en éphémère direct, donc
rien n'apparaît jamais publiquement ; les erreurs tardives (échec Bungie, table
vide, échec de rendu) suppriment le placeholder « thinking » public puis
envoient un followup éphémère.

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
    async def _fail_early(interaction: discord.Interaction, message: str) -> None:
        """Erreur AVANT le defer : réponse initiale éphémère.

        Réservée aux garde-fous instantanés (lecture du JSON local) : aucun
        defer n'a eu lieu, donc rien n'est jamais apparu publiquement."""
        try:
            await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException as e:
            log.warning(f"[LootTable] Réponse d'erreur non délivrée : {e}")

    @staticmethod
    async def _fail_late(interaction: discord.Interaction, message: str) -> None:
        """Erreur APRÈS le defer public : on efface le « thinking » public, puis
        on envoie l'erreur en followup éphémère.

        La suppression du placeholder est best-effort : s'il a déjà disparu,
        l'erreur reste délivrée."""
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
        # ── Garde-fous instantanés, AVANT tout defer ────────────────────
        # Tant que l'interaction n'est pas acquittée, l'erreur peut être une
        # réponse initiale éphémère : aucun placeholder public n'existe.
        if activite.startswith(_SEPARATOR_PREFIX):
            await self._fail_early(
                interaction,
                "Cette ligne est un séparateur de catégorie, pas une activité.\n"
                "-# Choisis une activité listée en dessous.",
            )
            return

        if activite not in {key for key, _, _ in list_activities()}:
            await self._fail_early(
                interaction,
                f"Activité inconnue : `{activite}`.\n"
                "-# Utilise l'autocomplétion pour voir les activités disponibles.",
            )
            return

        # ── Travail long ────────────────────────────────────────────────
        # Définitions Bungie non cachées + téléchargement d'icônes : on dépasse
        # facilement les 3 s d'ack. Defer PUBLIC : c'est lui qui rend le
        # message de succès public.
        await interaction.response.defer()

        try:
            activity = await get_loot_table(activite)
        except Exception as e:
            log.error(f"[LootTable] Résolution de « {activite} » échouée : {e}")
            await self._fail_late(
                interaction,
                "Impossible de récupérer cette table de butin pour l'instant.",
            )
            return

        # Course possible : le JSON est relu à chaque appel, il a pu être édité
        # entre le pré-contrôle ci-dessus et cette résolution.
        if activity is None or not activity.items:
            await self._fail_late(
                interaction, f"Aucun item à afficher pour `{activite}`."
            )
            return

        try:
            view, files = await build_loot_page(activity, 0)
        except Exception as e:
            log.error(f"[LootTable] Rendu de « {activite} » échoué : {e}")
            await self._fail_late(
                interaction, "Impossible d'afficher cette table de butin."
            )
            return

        message = await interaction.followup.send(view=view, files=files, wait=True)
        # Référence nécessaire pour désactiver les boutons à l'expiration.
        view.message = message


async def setup(bot: commands.Bot):
    await bot.add_cog(LootTable(bot))