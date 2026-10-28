# -*- coding: utf-8 -*-
"""Resets Bungie (17:00 UTC) : quotidien, hebdo, fenêtre de Xûr."""
import unittest
from datetime import datetime, timezone

from bot.bungie.reset import (
    FRIDAY,
    TUESDAY,
    last_reset,
    last_weekday_reset,
    next_reset,
    next_weekday_reset,
)
from bot.features.xur import is_xur_active


def utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


class ResetTests(unittest.TestCase):
    def test_last_reset_before_and_after_17h(self):
        self.assertEqual(last_reset(utc(2026, 10, 28, 16, 59)), utc(2026, 10, 27, 17))
        self.assertEqual(last_reset(utc(2026, 10, 28, 17, 0)), utc(2026, 10, 28, 17))

    def test_next_reset(self):
        self.assertEqual(next_reset(utc(2026, 10, 28, 12)), utc(2026, 10, 28, 17))

    def test_weekday_resets(self):
        # Mercredi 28/10/2026 : dernier mardi = 27/10, prochain vendredi = 30/10.
        now = utc(2026, 10, 28, 12)
        self.assertEqual(last_weekday_reset(TUESDAY, now), utc(2026, 10, 27, 17))
        self.assertEqual(next_weekday_reset(FRIDAY, now), utc(2026, 10, 30, 17))

    def test_next_weekday_reset_same_day_goes_to_next_week(self):
        self.assertEqual(
            next_weekday_reset(TUESDAY, utc(2026, 10, 27, 18)), utc(2026, 11, 3, 17)
        )

    def test_xur_window(self):
        self.assertFalse(is_xur_active(utc(2026, 10, 30, 16, 59)))  # vendredi avant reset
        self.assertTrue(is_xur_active(utc(2026, 10, 30, 17)))       # vendredi au reset
        self.assertTrue(is_xur_active(utc(2026, 11, 3, 16, 59)))    # mardi avant reset
        self.assertFalse(is_xur_active(utc(2026, 11, 3, 17)))       # mardi au reset


if __name__ == "__main__":
    unittest.main()
