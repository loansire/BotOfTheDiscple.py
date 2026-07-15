# -*- coding: utf-8 -*-
"""Composants interactifs de /botconfig (Components V2).

Navigation multi-pages pilotée par `node_id` (+ `page`) porté par la ConfigView :
- nœuds de l'arbre NAV_TREE (racine / jeu / catégorie / feuille)
- "topic:<topic>" pour la page détail d'un topic (sélecteurs salon + rôle)

Staging : chaque interaction ne modifie QUE l'état `pending` (ou la navigation)
puis reconstruit une vue neuve. Rien n'est persisté tant que l'utilisateur n'a
pas cliqué sur « Valider ».

Ce module ne connaît PAS l'arbre (évite un cycle d'import avec le builder) : le
builder construit les Sections de navigation et leur passe l'accessoire NavButton
(flèche) ciblant le nœud ; les boutons Retour reçoivent le nœud parent calculé
par le builder."""
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

# Sentinelle : « garder la valeur courante » lors d'un rebuild.
_KEEP = object()


def _rebuild(view, pending, node_id=_KEEP, page=_KEEP):
    """Instancie une vue neuve (même persisted, nouveau pending / navigation).

    `node_id` / `page` : _KEEP → conserve la valeur courante de la vue.
    """
    from bot.discord.configbot_view import ConfigView
    if node_id is _KEEP:
        node_id = view.node_id
    if page is _KEEP:
        page = view.page
    return ConfigView(view.user, view.guild, view.persisted, pending, node_id, page)


# ── Navigation (arbre + pagination) ────────────────────────────────────


class NavButton(ui.Button):
    """Accessoire ➡️ d'une Section de navigation : entre dans un nœud."""

    def __init__(self, target_node: str):
        super().__init__(emoji="➡️", style=discord.ButtonStyle.secondary)
        self.target_node = target_node

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), node_id=self.target_node, page=0)
        )


class BackButton(ui.Button):
    """Retour vers un nœud parent (fourni par le builder)."""

    def __init__(self, target_node: str):
        super().__init__(label="Retour", emoji="◀️", style=discord.ButtonStyle.secondary)
        self.target_node = target_node

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), node_id=self.target_node, page=0)
        )


class PrevPageButton(ui.Button):
    """Page précédente d'une feuille paginée."""

    def __init__(self, disabled: bool = False):
        super().__init__(emoji="◀️", style=discord.ButtonStyle.secondary, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), page=max(0, view.page - 1))
        )


class NextPageButton(ui.Button):
    """Page suivante d'une feuille paginée."""

    def __init__(self, disabled: bool = False):
        super().__init__(emoji="▶️", style=discord.ButtonStyle.secondary, disabled=disabled)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(view, copy.deepcopy(view.pending), page=view.page + 1)
        )


class TopicSettingsButton(ui.Button):
    """Accessoire ⚙️ d'une Section : ouvre la page détail d'un topic."""

    def __init__(self, topic: str):
        super().__init__(emoji="⚙️", style=discord.ButtonStyle.secondary)
        self.topic = topic

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        await interaction.response.edit_message(
            view=_rebuild(
                view, copy.deepcopy(view.pending),
                node_id=f"topic:{self.topic}", page=0,
            )
        )


# ── Selects par topic (page détail) ────────────────────────────────────


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

        # Reste sur la page détail du topic (node_id / page conservés).
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


# ── Boutons d'action (page détail) ─────────────────────────────────────


class ValidateButton(ui.Button):
    """Persiste tout le pending puis revient à la feuille parente du topic.

    Après persistance et acquittement, déclenche le routeur (handlers/topics.py)
    qui publie/supprime les messages des topics dont le salon a changé. Cette
    étape est best-effort : l'interaction étant déjà acquittée, une erreur de
    publication ne casse pas l'UX de config."""

    def __init__(self, return_node: str):
        super().__init__(label="Valider", emoji="💾", style=discord.ButtonStyle.success)
        self.return_node = return_node

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        guild = view.guild
        gid = str(guild.id)

        # Diff avant/après (forme load_config_state) AVANT de reconstruire.
        before = copy.deepcopy(view.persisted)
        after = copy.deepcopy(view.pending)

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

        # persisted ← pending, retour à la feuille parente (page « propre »).
        from bot.discord.configbot_view import ConfigView
        saved = copy.deepcopy(view.pending)
        new_view = ConfigView(
            view.user, guild, saved, copy.deepcopy(saved), self.return_node, 0
        )
        await interaction.response.edit_message(view=new_view)
        await interaction.followup.send("✅ Configuration enregistrée.", ephemeral=True)

        # Application des changements de salon (publication / suppression ciblées).
        from bot.discord.handlers.topics import apply_config_change
        try:
            await apply_config_change(interaction.client, gid, before, after)
        except Exception as e:
            log.error(f"[Config] Application des changements de salon échouée : {e}")


class ResetButton(ui.Button):
    """Annule les changements non validés (pending ← persisted) et revient à la
    feuille parente du topic."""

    def __init__(self, return_node: str):
        super().__init__(label="Annuler", emoji="↩️", style=discord.ButtonStyle.secondary)
        self.return_node = return_node

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        reverted = copy.deepcopy(view.persisted)
        await interaction.response.edit_message(
            view=_rebuild(view, reverted, node_id=self.return_node, page=0)
        )