# -*- coding: utf-8 -*-
"""Presenters (calcul) : contenu final rangé en base, sans réseau."""
import unittest
from unittest import mock

from bot.content.model import image_id_of
from bot.features.ada.models import AdaItem
from bot.features.ada.presenter import build_post as ada_post
from bot.features.eververse.models import EververseItem, EververseSection
from bot.features.eververse.presenter import build_post as ev_post
from bot.render.components import render

ICON = b"RIFF fake webp"


async def _icon(item_hash, icon, watermark, feature="xur"):
    return None if icon is None else ICON


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = mock.patch("bot.compute.get_item_icon", _icon)
        patcher.start()
        self.addCleanup(patcher.stop)


class AdaPresenterTests(_Base):
    async def test_items_become_sections_with_cost(self):
        items = [AdaItem(1, "Ornement A", icon="/a.png", cost_quantity=25000),
                 AdaItem(2, "Sans icône", icon=None, cost_quantity=10)]
        post = await ada_post(items)
        message = post.messages[0]
        kinds = [c.kind for c in message.components]
        self.assertEqual(kinds, ["text", "separator", "section"])  # l'item sans icône est ignoré
        self.assertIn("Actualisation:", message.components[0].text)
        self.assertEqual(message.components[2].text, "**Ornement A**\n<:Glimer:1526889023963136030> x25000")
        out = render(message, {image_id_of(ICON): ICON})
        self.assertEqual([f.filename for f in out.files], ["ada_1.webp"])

    async def test_chunking_and_refresh_only_on_first(self):
        items = [AdaItem(i, f"I{i}", icon="/i.png") for i in range(12)]
        post = await ada_post(items)
        self.assertEqual(len(post.messages), 2)
        self.assertIn("(1/2)", post.messages[0].components[0].text)
        self.assertNotIn("Actualisation", post.messages[1].components[0].text)

    async def test_cost_change_changes_hash(self):
        a = await ada_post([AdaItem(1, "A", icon="/a.png", cost_quantity=1)])
        b = await ada_post([AdaItem(1, "A", icon="/a.png", cost_quantity=2)])
        self.assertNotEqual(a.content_hash(), b.content_hash())


class EverversePresenterTests(_Base):
    async def test_class_label_and_empty_section_fallback(self):
        sections = [
            EververseSection("main", "Tess - Poussière brillante", "dust",
                             [EververseItem(1, "Orn", icon="/o.png", cost_quantity=500, class_label="Ornement Titan")]),
            EververseSection("other", "Tess - Poussière brillante", "dust", []),
        ]
        post = await ev_post(sections)
        self.assertEqual(len(post.messages), 2)
        self.assertEqual(post.messages[0].components[2].text,
                         "**Orn**\nOrnement Titan\n<:Dust:1526717375833964626> x500")
        self.assertEqual(post.messages[1].components[-1].text, "-# Aucun item pour cette rotation.")
        self.assertTrue(all("Actualisation" in m.components[0].text for m in post.messages))


class VanguardPresenterTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_category_has_header_icon_and_fallback(self):
        from bot.features.vanguard.constants import CATEGORIES
        from bot.features.vanguard.models import PortalCategory
        from bot.features.vanguard.presenter import build_vanguard_views

        key, _, label, icon_file = CATEGORIES[0]
        messages = await build_vanguard_views([PortalCategory(key, label, icon_file)], next_refresh_unix=123)
        kinds = [c.kind for c in messages[0].components]
        self.assertEqual(kinds, ["section", "separator", "text"])
        self.assertIn("Actualisation <t:123:R>", messages[0].components[0].text)
        self.assertEqual(messages[0].components[0].image_name, f"portal_{key}.png")


if __name__ == "__main__":
    unittest.main()
