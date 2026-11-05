# -*- coding: utf-8 -*-
"""Secteurs oubliés et raids : calcul → base (en mémoire) → messages Discord."""
import unittest
from datetime import timedelta
from unittest import mock

from bot.bungie.errors import BungieNotReadyError
from bot.features.weekly import handler
from bot.features.weekly.models import ActivityVariant, LostSector, WeeklyActivity
from bot.features.weekly.state import weekly_slot, weekly_state
from tests.fake_discord import FakeBot, FakeChannel, FakeGuild, subscriptions
from tests.storage_helpers import FakeContentStore, reset_memory


async def _banner(pgcr, feature, ratio, blur=0):
    return b"RIFF banner"


class WeeklyFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reset_memory()
        self.content = FakeContentStore()
        self.sectors = [LostSector("Secteur A", "Nessos", "/p.jpg",
                                   [ActivityVariant(1, "Expert", extra={"shields": {"Solaires": 2}})])]
        self.groups = [WeeklyActivity("Crypte", "Raid", 2043403989, "/c.jpg",
                                      variants=[ActivityVariant(5, "Standard", active_challenges=1)])]
        for patcher in (
            self.content.patch(),
            mock.patch("bot.features.weekly.presenter.get_banner", _banner),
            mock.patch("bot.features.weekly.handler.get_lost_sectors", self._sectors),
            mock.patch("bot.features.weekly.handler.get_raid_dungeon", self._groups),
            mock.patch("bot.compute.purge_icon_cache", lambda feature: None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ch = FakeChannel(11)
        self.bot = FakeBot([FakeGuild(1, {11: self.ch})])

    async def _sectors(self):
        return self.sectors

    async def _groups(self):
        return self.groups

    async def test_lost_sectors_publish_and_skip(self):
        with subscriptions("daily_lost_sector", {"1": ("11", "r")}):
            await handler.lost_sectors.publish(self.bot, strict=True)
            ids = weekly_slot("daily_lost_sector").get("1")["message_ids"]
            self.assertEqual(len(ids), 2)  # 1 secteur + ping
            text = self.ch.messages[int(ids[0])].view.children[0].children[0].content
            self.assertIn("# <:Secteur:1270042203577778246> Nessos", text)
            self.assertIn("<:So:1270714993553178624>2", text)
            self.assertTrue(weekly_state().last_signature("daily_lost_sector"))
            await handler.lost_sectors.publish(self.bot, strict=True)
            self.assertEqual(weekly_slot("daily_lost_sector").get("1")["message_ids"], ids)

    async def test_strict_refuses_empty(self):
        self.sectors = []
        with subscriptions("daily_lost_sector", {"1": ("11", None)}), \
                mock.patch("bot.features.weekly.freshness.bungie"):
            # Dans le délai de grâce : hold mode demandé à la pipeline.
            with mock.patch("bot.features.weekly.freshness.STALE_GRACE", timedelta(days=2)), \
                    self.assertRaises(BungieNotReadyError):
                await handler.lost_sectors.publish(self.bot, strict=True)
            # Délai écoulé : rien n'est publié (pas de message vide).
            with mock.patch("bot.features.weekly.freshness.STALE_GRACE", timedelta(0)):
                await handler.lost_sectors.publish(self.bot, strict=True)
        self.assertEqual(self.ch.messages, {})

    async def test_raid_message_keeps_rotation_button(self):
        with subscriptions("weekly_raid", {"1": ("11", "r")}):
            await handler.raids.publish(self.bot)
        msg = next(iter(self.ch.messages.values()))
        container = msg.view.children[0]
        row = container.children[-1]
        self.assertEqual(row.children[0].custom_id, "weekly:rota:raid")
        self.assertEqual(msg.view.children[-1].content, "<@&r>")  # ping injecté


if __name__ == "__main__":
    unittest.main()
