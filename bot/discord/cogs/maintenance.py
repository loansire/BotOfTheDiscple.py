# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.discord.publisher import publish_to_subscribers
from bot.embeds.maintenance import build_maintenance_embed
from bot.features.maintenance import (
    GAME_LABELS,
    extract_window,
    format_discord_message,
    get_maintenances,
)
from bot.features.maintenance_state import MaintenanceState
from bot.utils.logger import log

GAMES = ("destiny", "marathon")

_GAME_CHOICES = [
    app_commands.Choice(name="Destiny 2", value="destiny"),
    app_commands.Choice(name="Marathon", value="marathon"),
]


class Maintenance(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = MaintenanceState()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Tâche récurrente ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        log.debug("[Maintenance] poll #%d", self.poll.current_loop)
        for game in GAMES:
            try:
                await self._check_game(game)
            except Exception as e:
                log.error(f"[Maintenance] Erreur de poll pour {game} : {e}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    async def _check_game(self, game: str):
        data = await get_maintenances(game)  # déjà filtré "offline futur"
        if data is None:
            return

        updated_at = data.get("article_updated_at")
        st = self.state.get(game)

        # Pas de changement d'article → rien à faire
        if updated_at and updated_at == st.get("article_updated_at"):
            return

        new_state = {
            "article_updated_at": updated_at,
            "announced_offline_iso": st.get("announced_offline_iso"),
        }

        window = extract_window(data)
        if window is None:
            self.state.set(game, new_state)
            self.state.save()
            return

        # Déjà annoncée (même mise hors ligne) → on mémorise juste le nouvel updated_at
        if window["offline_iso"] == st.get("announced_offline_iso"):
            self.state.set(game, new_state)
            self.state.save()
            return

        await self._announce(game, data, window)
        new_state["announced_offline_iso"] = window["offline_iso"]
        self.state.set(game, new_state)
        self.state.save()
        log.info(f"[Maintenance] Alerte publiée pour {game} ({window['offline_iso']})")

    async def _announce(self, game: str, data: dict, window: dict):
        copy_text = format_discord_message(data)
        await publish_to_subscribers(
            self.bot,
            f"maintenance_{game}",
            build=lambda: build_maintenance_embed(window, copy_text),
        )

    # ---------- Commandes ----------
    @app_commands.command(
        name="maintenance",
        description="Affiche la maintenance à venir d'un jeu.",
    )
    @app_commands.describe(jeu="Jeu concerné")
    @app_commands.choices(jeu=_GAME_CHOICES)
    async def maintenance(self, interaction: discord.Interaction, jeu: str):
        await interaction.response.defer()
        data = await get_maintenances(jeu)
        window = extract_window(data) if data else None
        if window is None:
            await interaction.followup.send(
                f":x: Aucune maintenance à venir pour **{GAME_LABELS[jeu]}**.", ephemeral=True
            )
            return
        embed, files, view = build_maintenance_embed(window, format_discord_message(data))
        await interaction.followup.send(embed=embed, files=files, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Maintenance(bot))