# -*- coding: utf-8 -*-
"""Maintenance et news : publications événementielles calculées puis rendues."""
import unittest
from types import SimpleNamespace
from unittest import mock

import discord

from bot.discord.cogs.content_actions import ContentActions
from bot.features.maintenance.presenter import build_announcement_post, build_end_post
from bot.features.news.presenter import build_post as news_post
from bot.render.components import render
from tests.storage_helpers import FakeContentStore

WINDOW = {"game": "destiny", "game_label": "Destiny 2", "event_type": "Update 1.0",
          "offline_unix": 100, "online_unix": 200}
ARTICLE = {"Title": "TWID", "Description": "Desc", "Link": "/7/fr/News/x",
           "ImagePath": "https://img/x.jpg", "PubDate": "2026-11-05 | 17:00:00"}


class MaintenancePresenterTests(unittest.TestCase):
    def test_announcement_renders_like_before(self):
        post = build_announcement_post(WINDOW, "texte à copier")
        out = render(post.messages[0], {i: d for i, (d, _) in post.images().items()})
        self.assertEqual([f.name for f in out.embed.fields],
                         ["📝 __Commentaire(s)__", ":x: __Stop serveurs__",
                          ":white_check_mark: __Retour serveurs__", ":repeat: __Débute__"])
        self.assertIn("help.bungie.net", out.embed.author.name)
        self.assertTrue(out.embed.footer.text.startswith("BotOfTheDisciple • "))
        self.assertEqual(out.view.children[0].custom_id, "maintenance:copy:destiny")
        self.assertEqual(post.variants["copy"][0].components[0].text, "texte à copier")

    def test_end_post_has_its_own_topic(self):
        self.assertEqual(build_end_post("destiny").topic, "maintenance_destiny_end")


class NewsPresenterTests(unittest.TestCase):
    def test_variants_and_buttons(self):
        en_only = news_post("news_twid", ARTICLE, None)
        self.assertEqual(list(en_only.variants), ["en"])
        buttons = render(en_only.variants["en"][0], {}).view.children
        self.assertEqual([b.custom_id for b in buttons], ["news:news_twid:en", "news:news_twid:fr", "news:news_twid:check"])
        self.assertTrue(buttons[1].disabled)

        both = news_post("news_twid", ARTICLE, {**ARTICLE, "Title": "TWID FR"})
        self.assertEqual(sorted(both.variants), ["en", "fr"])
        fr = render(both.variants["fr"][0], {})
        self.assertIn("TWID FR", fr.embed.description)
        self.assertEqual(len(fr.view.children), 2)  # plus de 🔄


class ButtonActionTests(unittest.IsolatedAsyncioTestCase):
    async def test_news_check_without_fr_answers_ephemeral(self):
        content = FakeContentStore()
        with content.patch():
            await content.save_post(news_post("news_twid", ARTICLE, None))
            sent = {}
            response = SimpleNamespace(
                send_message=mock.AsyncMock(side_effect=lambda *a, **k: sent.update(k, text=a[0])),
                edit_message=mock.AsyncMock(),
            )
            interaction = SimpleNamespace(type=discord.InteractionType.component,
                                          data={"custom_id": "news:news_twid:check"}, response=response)
            await ContentActions(None).on_interaction(interaction)
        self.assertTrue(sent["ephemeral"])
        self.assertIn("pas encore", sent["text"])


if __name__ == "__main__":
    unittest.main()
