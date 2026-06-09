# -*- coding: utf-8 -*-
"""Cog weekly/daily : publie un message persistant (édité) par topic,
calé sur la détection du reset quotidien Bungie.

- weekly_raid_dungeon : liste raids/donjons (statique → édité seulement si change)
- daily_lost_sector   : secteurs du jour (change chaque reset → édité)
"""
import hashlib

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.bungie.reset import last_reset
from bot.discord.publisher import publish_persistent_view
from bot.embeds.weekly import build_lost_sectors_view, build_raid_dungeon_view
from bot.features.weekly import get_lost_sectors, get_raid_dungeon
from bot.features.weekly.state import WeeklyMessageState
from bot.utils.logger import log


def _content_hash(parts) -> str:
    """Hash court et stable d'une liste de chaînes (ordre indépendant)."""
    joined = "|".join(sorted(parts))
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


class Weekly(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = WeeklyMessageState()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Détection du reset ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        current = last_reset().isoformat()
        if current == self.state.last_reset_iso:
            return  # reset déjà traité (rattrapage automatique au redémarrage)

        log.info("[Weekly] Nouveau reset détecté — publication des activités.")
        try:
            await self._publish_all()
        except Exception as e:
            log.error(f"[Weekly] Échec de publication : {e}")
            return

        self.state.last_reset_iso = current
        self.state.save()

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    # ---------- Publication ----------
    async def _publish_all(self):
        rd = await get_raid_dungeon()
        if rd:
            rd_hash = _content_hash(g.base_name for g in rd)
            await publish_persistent_view(
                self.bot,
                "weekly_raid_dungeon",
                build_view=lambda data=rd: self._build_rd(data),
                content_hash=rd_hash,
                state=self.state,
            )

        ls = await get_lost_sectors()
        if ls:
            ls_hash = _content_hash(
                str(v.activity_hash) for s in ls for v in s.variants
            )
            await publish_persistent_view(
                self.bot,
                "daily_lost_sector",
                build_view=lambda data=ls: self._build_ls(data),
                content_hash=ls_hash,
                state=self.state,
            )

    async def _build_rd(self, rd):
        return build_raid_dungeon_view(rd), []

    async def _build_ls(self, ls):
        return await build_lost_sectors_view(ls)

    # ---------- Commande admin ----------
    @app_commands.command(
        name="weekly-refresh",
        description="Republie/actualise les activités weekly & daily.",
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def weekly_refresh(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await self._publish_all()
        except Exception as e:
            log.error(f"[Weekly] /weekly-refresh a échoué : {e}")
            await interaction.followup.send(":x: Échec de la republication.", ephemeral=True)
            return
        await interaction.followup.send("✅ Activités weekly & daily actualisées.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Weekly(bot))