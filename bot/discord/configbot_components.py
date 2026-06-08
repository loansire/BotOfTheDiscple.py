# -*- coding: utf-8 -*-
"""Composants interactifs de /botconfig (Components V2).

Navigation à 2 niveaux :
- page principale (current_topic=None) : résumé + bouton ⚙️ par topic
- page détail (current_topic=<topic>) : listes déroulantes + Valider/Annuler

Staging : chaque interaction ne modifie QUE l'état `pending` (ou la navigation)
puis reconstruit une vue neuve. Rien n'est persisté tant que l'utilisateur n'a
pas cliqué sur « Valider ».
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

_THREAD_TYPES = {
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
}

# Sentinelle : « garder la page courante » lors d'un rebuild.
_KEEP = object()


def _rebuild(view, pending, current_topic=_KEEP):
    """Instancie une vue neuve avec le même persisted et le nouveau pending.

    `current_topic` :
        - _KEEP  → on reste sur la page courante (cas des selects)
        - None   → page principale
        - <str>  → page détail du topic
    """
    from bot.discord.configbot_view import ConfigView
    if current_topic is _KEEP:
        current_topic = view.current_topic
    return ConfigView(view.user, view.guild, view.persisted, pending, current_topic)


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


# ── Navigation ─────────────────────────────────────────────────────────


class TopicSettingsButton(ui.Button):
    """Accessoire ⚙️ d'une Section : ouvre la page détail du topic."""

    def __init__(self, topic: str):
        super().__init__(emoji="⚙️", style=discord.ButtonStyle.secondary)
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), current_topic=self.topic)
        )


class BackButton(ui.Button):
    """Retour à la page principale (conserve le pending tel quel)."""

    def __init__(self):
        super().__init__(label="Retour", emoji="◀️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), current_topic=None)
        )


# ── Boutons d'action (page détail) ─────────────────────────────────────


class ValidateButton(ui.Button):
    """Persiste tout le pending puis revient à la page principale."""

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

        # persisted ← pending, retour accueil (page « propre »)
        from bot.discord.configbot_view import ConfigView
        saved = copy.deepcopy(view.pending)
        new_view = ConfigView(view.user, guild, saved, copy.deepcopy(saved), current_topic=None)
        await interaction.response.edit_message(view=new_view)
        await interaction.followup.send("✅ Configuration enregistrée.", ephemeral=True)


class ResetButton(ui.Button):
    """Annule les changements non validés (pending ← persisted) et revient
    à la page principale."""

    def __init__(self):
        super().__init__(label="Annuler", emoji="↩️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        reverted = copy.deepcopy(view.persisted)
        await interaction.response.edit_message(
            view=_rebuild(view, reverted, current_topic=None)
        )