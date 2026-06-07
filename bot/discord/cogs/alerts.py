# -*- coding: utf-8 -*-
"""Cog d'alertes News : abonnement + polling auto (TWID/TWAB & patch notes)."""
import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.discord.publisher import publish_to_subscribers
from bot.embeds.news import build_news_alert
from bot.features.news import get_latest_article
from bot.features.news_state import NewsState
from bot.utils.logger import log
from bot.utils.subscriptions import subscribe, unsubscribe, current_destination

# type d'alerte → (keyword Bungie, topic d'abonnement, libellé)
NEWS_TYPES = {
    "twid": {"keyword": "twid", "topic": "news_twid", "label": "TWID/TWAB"},
    "patch_note": {"keyword": "destiny_update", "topic": "news_patch_note", "label": "Patch Note"},
}

# Langue des annonces automatiques
AUTO_LANG = "en"

_TYPE_CHOICES = [
    app_commands.Choice(name="TWID/TWAB", value="twid"),
    app_commands.Choice(name="Patch Note", value="patch_note"),
]
_ACTION_CHOICES = [
    app_commands.Choice(name="S'abonner", value="subscribe"),
    app_commands.Choice(name="Se désabonner", value="unsubscribe"),
]


class NewsAlerts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = NewsState()
        self.poll.start()

    def cog_unload(self):
        self.poll.cancel()

    # ---------- Polling ----------
    @tasks.loop(minutes=1)
    async def poll(self):
        log.debug("[NewsAlerts] poll #%d", self.poll.current_loop)
        for alert_type, cfg in NEWS_TYPES.items():
            try:
                await self._check(alert_type, cfg)
            except Exception as e:
                log.error(f"[NewsAlerts] Erreur de poll pour {alert_type} : {e}")

    @poll.before_loop
    async def _before_poll(self):
        await self.bot.wait_until_ready()

    async def _check(self, alert_type: str, cfg: dict):
        article, is_both = await get_latest_article(AUTO_LANG, cfg["keyword"])
        if not article:
            return

        article_id = article.get("UniqueIdentifier", "")
        if not article_id or article_id == self.state.last_id(alert_type):
            return  # rien de nouveau

        await publish_to_subscribers(
            self.bot,
            cfg["topic"],
            build=lambda a=article, k=cfg["keyword"]: build_news_alert(a, AUTO_LANG, is_both, k),
        )
        self.state.set_last_id(alert_type, article_id)
        self.state.save()
        log.info(f"[NewsAlerts] Nouvel article {alert_type} publié : {article_id}")

    # ---------- Commande d'abonnement ----------
    @app_commands.command(
        name="news-alert",
        description="S'abonner / se désabonner aux alertes d'actualités Destiny.",
    )
    @app_commands.describe(
        type="Type d'actualité",
        action="Action à effectuer",
        role="Rôle à mentionner lors des alertes (optionnel, abonnement uniquement)",
    )
    @app_commands.choices(type=_TYPE_CHOICES, action=_ACTION_CHOICES)
    @app_commands.default_permissions(administrator=True)
    async def news_alert(
            self,
            interaction: discord.Interaction,
            type: str,
            action: str,
            role: discord.Role = None,
    ):
        cfg = NEWS_TYPES[type]
        topic = cfg["topic"]
        label = cfg["label"]
        guild_id = str(interaction.guild.id)
        channel_id = str(interaction.channel.id)
        is_thread = isinstance(interaction.channel, discord.Thread)

        if action == "subscribe":
            role_id = str(role.id) if role else None
            if subscribe(topic, guild_id, channel_id, is_thread, role_id):
                suffix = f" — mention <@&{role_id}>" if role_id else ""
                await interaction.response.send_message(
                    f":white_check_mark: <#{channel_id}> abonné aux alertes **{label}**{suffix}.",
                    ephemeral=True,
                )
            else:
                existing = current_destination(topic, guild_id)
                where = f" (<#{existing}>)" if existing else ""
                await interaction.response.send_message(
                    f":warning: Ce serveur a déjà un salon configuré pour les alertes **{label}**{where}. "
                    f"Désabonnez-le d'abord avant d'en configurer un nouveau.",
                    ephemeral=True,
                )
        else:
            removed = unsubscribe(topic, guild_id, channel_id, is_thread)
            msg = (
                f":wastebasket: <#{channel_id}> désabonné des alertes **{label}**."
                if removed
                else f":x: Ce salon n'était pas abonné aux alertes **{label}**."
            )
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsAlerts(bot))