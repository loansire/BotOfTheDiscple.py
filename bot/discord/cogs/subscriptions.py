# -*- coding: utf-8 -*-
"""Cog unique d'abonnement aux alertes (maintenance + news), toggle implicite.

Une seule commande `/alerte` remplace `maintenance-alert` et `news-alert`.
Comportement : si le salon/thread courant est déjà abonné au type choisi,
la commande le désabonne ; sinon elle l'abonne (avec rôle optionnel).
Plusieurs types d'alerte peuvent coexister dans un même salon.
"""
import discord
from discord import app_commands
from discord.ext import commands

from bot.utils.subscriptions import is_subscribed, subscribe, unsubscribe

# Valeur du choix → (topic d'abonnement, libellé affiché)
ALERT_TYPES = {
    "maintenance_destiny": ("maintenance_destiny", "Maintenance Destiny 2"),
    "maintenance_marathon": ("maintenance_marathon", "Maintenance Marathon"),
    "patch_note": ("news_patch_note", "Patch Note D2"),
    "twid": ("news_twid", "TWID/TWAB"),
}

_TYPE_CHOICES = [
    app_commands.Choice(name="Maintenance Destiny 2", value="maintenance_destiny"),
    app_commands.Choice(name="Maintenance Marathon", value="maintenance_marathon"),
    app_commands.Choice(name="Patch Note D2", value="patch_note"),
    app_commands.Choice(name="TWID/TWAB", value="twid"),
]


class Subscriptions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="alerte",
        description="Active/désactive une alerte dans ce salon (toggle implicite).",
    )
    @app_commands.describe(
        type="Type d'alerte à (dés)activer dans ce salon",
        role="Rôle à mentionner lors des alertes (abonnement uniquement, optionnel)",
    )
    @app_commands.choices(type=_TYPE_CHOICES)
    @app_commands.default_permissions(administrator=True)
    async def alerte(
        self,
        interaction: discord.Interaction,
        type: str,
        role: discord.Role = None,
    ):
        topic, label = ALERT_TYPES[type]
        guild_id = str(interaction.guild.id)
        dest_id = str(interaction.channel.id)
        is_thread = isinstance(interaction.channel, discord.Thread)

        if is_subscribed(topic, guild_id, dest_id):
            unsubscribe(topic, guild_id, dest_id)
            await interaction.response.send_message(
                f":wastebasket: <#{dest_id}> désabonné des alertes **{label}**.",
                ephemeral=True,
            )
        else:
            role_id = str(role.id) if role else None
            subscribe(
                topic,
                guild_id,
                dest_id,
                is_thread=is_thread,
                guild_name=interaction.guild.name,
                channel_name=interaction.channel.name,
                role_id=role_id,
            )
            suffix = f" — mention <@&{role_id}>" if role_id else ""
            await interaction.response.send_message(
                f":white_check_mark: <#{dest_id}> abonné aux alertes **{label}**{suffix}.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(Subscriptions(bot))