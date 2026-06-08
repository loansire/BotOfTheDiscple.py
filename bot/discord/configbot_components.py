# -*- coding: utf-8 -*-
"""Composants interactifs de /botconfig (Components V2).

Logique de staging : chaque interaction ne modifie QUE l'état `pending` de la
vue puis reconstruit une vue neuve (edit_message). Rien n'est persisté tant
que l'utilisateur n'a pas cliqué sur « Valider ».
"""
import copy

import discord
from discord import ui

from bot.utils.logger import log
from bot.utils.subscriptions import TOPICS, set_topic_destination

# Types de salons proposés dans le ChannelSelect
_CHANNEL_TYPES = [
    discord.ChannelType.text,
    discord.ChannelType.news,
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
]

# Les valeurs d'un ChannelSelect sont des AppCommandChannel/Thread (objets
# partiels) → on détecte les threads via .type, jamais via isinstance(Thread).
_THREAD_TYPES = {
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
}


def _rebuild(view, pending):
    """Instancie une vue neuve avec le même persisted et le nouveau pending."""
    from bot.discord.configbot_view import ConfigView
    return ConfigView(view.user, view.guild, view.persisted, pending)


# ── Selects par topic ──────────────────────────────────────────────────


class ConfigChannelSelect(ui.ChannelSelect):
    """Choix du salon/thread cible pour un topic donné."""

    def __init__(self, topic: str, default_channel=None):
        kwargs = {}
        if default_channel is not None:
            kwargs["default_values"] = [
                discord.SelectDefaultValue.from_channel(default_channel)
            ]
        super().__init__(
            channel_types=_CHANNEL_TYPES,
            placeholder="Salon ou thread des alertes…",
            min_values=0,
            max_values=1,
            **kwargs,
        )
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        pending = copy.deepcopy(view.pending)
        slot = pending[self.topic]

        if self.values:
            ch = self.values[0]
            slot["channel_id"] = str(ch.id)
            slot["is_thread"] = ch.type in _THREAD_TYPES
        else:
            # Salon retiré → on désactive le topic et on purge le rôle associé
            slot["channel_id"] = None
            slot["is_thread"] = False
            slot["role_id"] = None

        await interaction.response.edit_message(view=_rebuild(view, pending))


class ConfigRoleSelect(ui.RoleSelect):
    """Choix du rôle à mentionner pour un topic donné."""

    def __init__(self, topic: str, default_role=None, disabled: bool = False):
        kwargs = {}
        if default_role is not None:
            kwargs["default_values"] = [
                discord.SelectDefaultValue.from_role(default_role)
            ]
        super().__init__(
            placeholder=(
                "Choisis d'abord un salon" if disabled else "Rôle à mentionner (optionnel)…"
            ),
            min_values=0,
            max_values=1,
            disabled=disabled,
            **kwargs,
        )
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        pending = copy.deepcopy(view.pending)
        pending[self.topic]["role_id"] = str(self.values[0].id) if self.values else None
        await interaction.response.edit_message(view=_rebuild(view, pending))


# ── Boutons d'action ───────────────────────────────────────────────────


class ValidateButton(ui.Button):
    """Persiste l'ensemble du pending puis rafraîchit (le bouton disparaît)."""

    def __init__(self):
        super().__init__(label="Valider", emoji="💾", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        guild = view.guild
        gid = str(guild.id)

        for topic in TOPICS:
            p = view.pending[topic]
            ch = guild.get_channel_or_thread(int(p["channel_id"])) if p["channel_id"] else None
            set_topic_destination(
                topic,
                gid,
                p["channel_id"],
                is_thread=p["is_thread"],
                role_id=p["role_id"],
                guild_name=guild.name,
                channel_name=ch.name if ch else None,
            )
        log.info(f"[Guild {gid}] Configuration des alertes mise à jour par {interaction.user}")

        # persisted = pending → plus de diff → bouton Valider masqué
        saved = copy.deepcopy(view.pending)
        new_view = _rebuild(view, saved)
        new_view.persisted = saved
        await interaction.response.edit_message(view=new_view)
        await interaction.followup.send(
            "✅ Configuration enregistrée.", ephemeral=True
        )


class ResetButton(ui.Button):
    """Annule les changements non validés (pending ← persisted)."""

    def __init__(self):
        super().__init__(label="Annuler", emoji="↩️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        pending = copy.deepcopy(view.persisted)
        await interaction.response.edit_message(view=_rebuild(view, pending))
