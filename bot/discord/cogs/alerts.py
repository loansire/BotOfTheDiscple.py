# -*- coding: utf-8 -*-
"""Cog d'alertes News : polling auto (TWID/TWAB & patch notes).

L'abonnement est désormais géré par la commande unifiée `/alerte`
(cf. bot.discord.cogs.subscriptions). Ce cog ne conserve que le polling.
"""
from discord.ext import commands, tasks

from bot.discord.publisher import publish_to_subscribers
from bot.embeds.news import build_news_alert
from bot.features.news import get_latest_article
from bot.features.news_state import NewsState
from bot.utils.logger import log

# type d'alerte → (keyword Bungie, topic d'abonnement, libellé)
NEWS_TYPES = {
    "twid": {"keyword": "twid", "topic": "news_twid", "label": "TWID/TWAB"},
    "patch_note": {"keyword": "destiny_update", "topic": "news_patch_note", "label": "Patch Note"},
}

# Langue des annonces automatiques
AUTO_LANG = "en"


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


async def setup(bot: commands.Bot):
    await bot.add_cog(NewsAlerts(bot))