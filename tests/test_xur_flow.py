# -*- coding: utf-8 -*-
"""Xûr de bout en bout : calcul → base (en mémoire) → messages Discord."""
import unittest
from unittest import mock

from bot.features.xur import handler
from bot.features.xur.models import XurItem, XurVendor
from bot.features.xur.state import xur_state
from tests.fake_discord import FakeBot, FakeChannel, FakeGuild, subscriptions
from tests.storage_helpers import FakeContentStore, reset_memory


async def _icon(item_hash, icon, watermark, feature="xur"):
    return b"RIFF icon" + str(item_hash).encode()


async def _vendor_icon(key, path):
    return b"RIFF vendor", f"vendor_{key}_246.webp"


def _vendors(cost=29):
    return [
        XurVendor("exotics-weapons", "ARMES EXOTIQUES", "<:Xur:1>", large_icon="/v.png",
                  items=[XurItem(10, "Arme", icon="/a.png", cost_quantity=cost)]),
        XurVendor("materials", "OFFRE MATERIAUX", "<:Xur:1>", items=[]),
    ]


class XurFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reset_memory()
        self.content = FakeContentStore()
        self.vendors = _vendors()
        for patcher in (
            self.content.patch(),
            mock.patch("bot.compute.get_item_icon", _icon),
            mock.patch("bot.features.xur.presenter.get_vendor_icon", _vendor_icon),
            mock.patch("bot.features.xur.handler.get_xur", self._get_xur),
            mock.patch("bot.compute.purge_icon_cache", lambda feature: None),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ch = FakeChannel(11)
        self.bot = FakeBot([FakeGuild(1, {11: self.ch})])

    async def _get_xur(self):
        return self.vendors

    async def test_arrival_then_departure(self):
        with subscriptions("xur", {"1": ("11", "role1")}):
            await handler.publish_arrival(self.bot)
            entry = xur_state().get("1")
            # statut + 1 catégorie (vendor vide ignoré) + ping
            self.assertEqual(len(self.ch.messages), 3)
            self.assertEqual(self.ch.pings, ["<@&role1>"])
            status = self.ch.messages[int(entry["status_id"])]
            self.assertIn("XÛR EST LÀ", status.view.children[0].children[0].content)
            self.assertEqual(entry["hash"], self.content.posts["xur"].stored_hash)

            await handler.publish_arrival(self.bot)  # même contenu → rien ne bouge
            self.assertEqual(xur_state().get("1"), entry)

            await handler.mark_departed(self.bot)
            self.assertEqual(len(self.ch.messages), 1)  # catégories + ping supprimés
            self.assertIn("N'EST PAS LÀ", status.view.children[0].children[0].content)

    async def test_cost_change_reposts(self):
        with subscriptions("xur", {"1": ("11", None)}):
            await handler.publish_arrival(self.bot)
            first = xur_state().get("1")["category_ids"]
            self.vendors = _vendors(cost=30)
            await handler.publish_arrival(self.bot)
            self.assertNotEqual(xur_state().get("1")["category_ids"], first)


if __name__ == "__main__":
    unittest.main()
