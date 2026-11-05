# -*- coding: utf-8 -*-
"""Loot table et Wishwall : pages calculées en base, relues au clic."""
import unittest
from types import SimpleNamespace
from unittest import mock

import discord

from bot.discord.cogs.content_actions import ContentActions
from bot.features.loottable.models import LootActivity, LootItem
from bot.features.loottable.presenter import build_index_post, build_post as loot_post
from bot.features.wishwall.presenter import build_post as wish_post
from bot.render.components import render
from tests.storage_helpers import FakeContentStore


async def _icon(item_hash, icon, watermark, feature="xur"):
    return b"RIFF icon" + str(item_hash).encode()


def _interaction(custom_id, values=None):
    response = SimpleNamespace(send_message=mock.AsyncMock(), edit_message=mock.AsyncMock())
    data = {"custom_id": custom_id, **({"values": values} if values else {})}
    return SimpleNamespace(type=discord.InteractionType.component, data=data, response=response)


class LootTableTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        patcher = mock.patch("bot.compute.get_item_icon", _icon)
        patcher.start()
        self.addCleanup(patcher.stop)
        items = [LootItem(i, f"Arme {i}", icon="/i.png", is_exotic=i == 0) for i in range(12)]
        self.post = await loot_post(LootActivity("rappel", "Rappel", "Rappel.png", "prestige", items))

    def test_pages_and_pager(self):
        self.assertEqual(sorted(self.post.variants), ["p1", "p2"])
        page1 = render(self.post.variants["p1"][0], {})
        buttons = page1.view.children[0].children[-1].children
        self.assertEqual([b.custom_id for b in buttons], ["loot:rappel:0", "loot:rappel:2"])
        self.assertEqual([b.disabled for b in buttons], [True, False])
        self.assertIn("RAPPEL (1/2)", self.post.variants["p1"][0].components[0].text)

    def test_index_keeps_order_and_groups(self):
        index = build_index_post([("rappel", "Rappel", "prestige"), ("nessos", "Nessos", "destination")])
        options = index.messages[0].components
        self.assertEqual([o.btn_action for o in options], ["rappel", "nessos"])
        self.assertIn("PRESTIGE", options[0].title)

    async def test_page_click_reads_database(self):
        content = FakeContentStore()
        with content.patch():
            await content.save_post(self.post)
            interaction = _interaction("loot:rappel:2")
            await ContentActions(None).on_interaction(interaction)
        kwargs = interaction.response.edit_message.call_args.kwargs
        self.assertEqual(len(kwargs["attachments"]), 4)  # bannière + icônes des 3 items de la page 2
        self.assertIsNone(kwargs.get("embed"))


class WishwallTests(unittest.IsolatedAsyncioTestCase):
    async def test_select_switches_variant(self):
        wishes = [{"nom": "Premier vœu - Clé", "description": "Desc", "image": "Voeu1.webp", "BoutonName": None}]
        content = FakeContentStore()
        with mock.patch("bot.features.wishwall.presenter.load_wishes", return_value=wishes), content.patch():
            post = wish_post()
            self.assertEqual(sorted(post.variants), ["0", "intro"])
            intro = render(post.variants["intro"][0], {})
            self.assertEqual(intro.view.children[0].options[0].label, "Clé")
            await content.save_post(post)
            interaction = _interaction("wishwall:select", ["0"])
            await ContentActions(None).on_interaction(interaction)
        embed = interaction.response.edit_message.call_args.kwargs["embed"]
        self.assertIn("Premier vœu", embed.description)


if __name__ == "__main__":
    unittest.main()
