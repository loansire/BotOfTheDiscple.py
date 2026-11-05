# -*- coding: utf-8 -*-
"""Marqueurs d'emotes : stockés indépendamment du bot, résolus par bot."""
import unittest

from bot.content.model import Message, button, text
from bot.render import components
from bot.render.emotes import BOTS, EMOTES, e, resolve


class EmoteTests(unittest.TestCase):
    def test_marker_and_resolution_per_bot(self):
        self.assertEqual(e("topic.xur"), "{e:topic.xur}")
        self.assertEqual(resolve("# {e:topic.xur} Xûr", "live"), "# <:Xur:1527021351368659205> Xûr")
        # Clé absente pour un bot : emote omise, jamais de marqueur brut.
        self.assertEqual(resolve("# {e:topic.xur} Xûr", "bot-sans-table"), "#  Xûr")
        self.assertIsNone(resolve(None, "live"))

    def test_unknown_key_rejected(self):
        with self.assertRaises(KeyError):
            e("cle.inexistante")

    def test_table_rows_well_formed(self):
        for key, row in EMOTES.items():
            with self.subTest(key=key):
                self.assertEqual(len(row), 1 + len(BOTS))
                self.assertTrue(row[0])
                self.assertTrue(all(i is None or isinstance(i, int) for i in row[1:]))

    def test_render_resolves_without_touching_stored_message(self):
        msg = Message().add(text(f"{e('currency.dust')} x5"))
        msg.add(button("Voir", "act", emoji=e("topic.ada")))
        resolved = components._resolve_emotes(msg)
        self.assertNotIn("{e:", resolved.components[0].text)
        self.assertEqual(msg.components[0].text, "{e:currency.dust} x5")
        self.assertNotIn("{e:", resolved.components[1].btn_emoji or "")


if __name__ == "__main__":
    unittest.main()
