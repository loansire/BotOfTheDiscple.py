# -*- coding: utf-8 -*-
"""Rotations fixes (Distorsion horaire, Défi ascendant hebdo) et leurs hash."""
import unittest
from datetime import timedelta

from bot.features import ascendant, distortion
from bot.features.ascendant.constants import CONTRAT_VERS_DEFI, DEFIS_ORDRE
from bot.features.distortion.constants import ORDER


class DistortionTests(unittest.TestCase):
    def test_anchor_is_first_destination(self):
        win = distortion.current_window(distortion.ANCHOR)
        self.assertEqual((win.key, win.index), (ORDER[0], 0))
        self.assertEqual(win.end - win.start, timedelta(hours=1))

    def test_cycle_wraps(self):
        now = distortion.ANCHOR + timedelta(hours=len(ORDER), minutes=30)
        self.assertEqual(distortion.current_window(now).key, ORDER[0])

    def test_before_anchor(self):
        win = distortion.current_window(distortion.ANCHOR - timedelta(minutes=1))
        self.assertEqual((win.key, win.index), (ORDER[-1], -1))

    def test_upcoming(self):
        ups = distortion.upcoming_windows(distortion.ANCHOR)
        self.assertEqual([w.key for w in ups], list(ORDER[1:]))
        self.assertEqual(ups[0].start, distortion.ANCHOR + timedelta(hours=1))


class AscendantTests(unittest.TestCase):
    def test_anchor_and_cycle(self):
        anchor = ascendant.ANCHOR
        self.assertEqual(ascendant.current_window(anchor).key, DEFIS_ORDRE[0])
        later = anchor + timedelta(weeks=len(DEFIS_ORDRE) + 1, hours=1)
        win = ascendant.current_window(later)
        self.assertEqual((win.key, win.index), (DEFIS_ORDRE[1], len(DEFIS_ORDRE) + 1))

    def test_upcoming(self):
        ups = ascendant.upcoming_windows(ascendant.ANCHOR, count=2)
        self.assertEqual([w.key for w in ups], list(DEFIS_ORDRE[1:3]))

    def test_resolve_formula_and_contract(self):
        now = ascendant.ANCHOR + timedelta(hours=1)
        self.assertEqual(ascendant.resolve(None, now)["source"], "formule")
        contrat = next(h for h, k in CONTRAT_VERS_DEFI.items() if k == DEFIS_ORDRE[2])
        state = ascendant.resolve(contrat, now)
        self.assertEqual((state["source"], state["cle"]), ("contrat", DEFIS_ORDRE[2]))
        # Contrat inconnu → repli formule.
        self.assertEqual(ascendant.resolve(1, now)["cle"], DEFIS_ORDRE[0])


class ContentHashTests(unittest.TestCase):
    def test_rotation_posts_change_with_the_period(self):
        from bot.features.ascendant.presenter import build_post as asc_post
        from bot.features.distortion.presenter import build_post as dis_post

        start = distortion.ANCHOR
        self.assertEqual(dis_post(start).content_hash(), dis_post(start + timedelta(minutes=59)).content_hash())
        self.assertNotEqual(dis_post(start).content_hash(), dis_post(start + timedelta(hours=1)).content_hash())
        first = dis_post(start).messages[0]
        self.assertIn(f"## {ORDER[0]}", first.components[0].text)
        self.assertEqual(first.components[1].kind, "gallery")  # image du lieu stockée

        post = asc_post(ascendant.ANCHOR)
        self.assertIn("Défi ascendant de la semaine", post.messages[0].components[0].text)
        self.assertNotEqual(post.content_hash(), asc_post(ascendant.ANCHOR + timedelta(weeks=1)).content_hash())

    def test_parts_hash_is_order_independent(self):
        from bot.publishing.primitives import content_hash

        self.assertEqual(content_hash(["a", "b"]), content_hash(["b", "a"]))
        self.assertNotEqual(content_hash(["a"]), content_hash(["b"]))
        self.assertEqual(len(content_hash(["a"])), 16)


if __name__ == "__main__":
    unittest.main()
