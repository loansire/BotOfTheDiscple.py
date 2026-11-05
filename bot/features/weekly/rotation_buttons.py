# -*- coding: utf-8 -*-
"""Bouton « Rotation prédictive » des messages raids / donjons.

Le message hebdomadaire est PERSISTANT (supprimé/reposté à chaque reset, et
survivant aux redémarrages du bot) : le bouton doit donc l'être aussi.

Deux conséquences :
1. `custom_id` STATIQUE — aucune donnée n'y est encodée. C'est possible parce
   que l'ancrage de la prédiction est recalculé au clic depuis l'API : le
   bouton n'a rien à mémoriser. Un vieux message d'il y a trois semaines
   affichera donc la rotation correcte, pas une rotation périmée.
2. La vue doit être enregistrée au démarrage via `bot.add_view()` — cf.
   cogs/rotation.py. Sans ça, un clic sur un message antérieur au dernier
   redémarrage resterait sans réponse.

Le fetch au clic est volontaire : `get_raid_dungeon()` est déjà mis en cache
côté client Bungie (cache profil aligné sur le reset), donc le coût réel est
quasi nul et on évite de trimballer un état.
"""
from __future__ import annotations

import discord
from discord import ui

from bot.core.logger import log
from bot.publishing.content_source import snapshot

_LABELS = {
    "raid": "Rotation prédictive",
    "dungeon": "Rotation prédictive",
}


class RotationButton(ui.Button):
    """Ouvre la rotation prédictive du cycle complet, en éphémère."""

    def __init__(self, kind: str):
        super().__init__(
            label=_LABELS[kind],
            emoji="🗓️",
            style=discord.ButtonStyle.primary,
            custom_id=f"weekly:rota:{kind}",
        )
        self.kind = kind

    async def callback(self, interaction: discord.Interaction):
        # defer(ephemeral=True) fige l'interaction en éphémère : TOUS les
        # followups le seront, y compris le message d'erreur.
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Rotation précalculée au reset (bot/features/weekly/handler.py) :
        # simple lecture en base, aucun appel Bungie.
        try:
            snap = await snapshot(f"rotation_{self.kind}")
        except Exception as e:
            log.error(f"[Rotation] Lecture en base échouée ({self.kind}) : {e}")
            snap = None

        if snap is None:
            await interaction.followup.send(
                "⚠️ La rotation de la semaine n'est pas encore disponible. "
                "Réessaie dans quelques minutes.",
                ephemeral=True,
            )
            return

        out = snap.render()
        await interaction.followup.send(view=out.view, files=out.files, ephemeral=True)


class RotationActionRow(ui.ActionRow):
    """Ligne d'action ajoutée au bas du container raids/donjons."""

    def __init__(self, kind: str):
        super().__init__()
        self.add_item(RotationButton(kind))


class RotationPersistentView(ui.LayoutView):
    """Vue de DISPATCH enregistrée une fois au démarrage.

    Elle n'est jamais envoyée : elle sert uniquement à mapper les custom_id
    'weekly:rota:*' vers leurs callbacks pour les messages déjà en ligne."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RotationActionRow("raid"))
        self.add_item(RotationActionRow("dungeon"))