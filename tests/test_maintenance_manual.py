# -*- coding: utf-8 -*-
"""Saisie manuelle des maintenances : jour anglais, AM/PM, fuseaux → Unix."""
import unittest
from datetime import datetime, timezone

from bot.features.maintenance.manual import (
    ManualInputError,
    build_manual_window,
    parse_clock,
    parse_day,
    parse_window,
)

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def _utc(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


class ParseDayTests(unittest.TestCase):
    def test_formats(self):
        for text in ("October 20", "oct 20", "Oct. 20", "20 October", "October 20th", " October 20, "):
            self.assertEqual(parse_day(text), (10, 20), text)

    def test_invalid(self):
        for text in ("Octobre 20", "20/10", "October", "2026"):
            with self.assertRaises(ManualInputError, msg=text):
                parse_day(text)


class ParseClockTests(unittest.TestCase):
    def test_am_pm(self):
        self.assertEqual(parse_clock("8:30 AM PDT")[:2], (8, 30))
        self.assertEqual(parse_clock("12:15 AM")[:2], (0, 15))
        self.assertEqual(parse_clock("12 PM")[:2], (12, 0))
        self.assertEqual(parse_clock("1:05pm PST")[:2], (13, 5))
        self.assertEqual(parse_clock("17:45 UTC")[:2], (17, 45))

    def test_invalid(self):
        for text in ("13:00 PM", "0 AM", "8:75 AM", "25:00", "8:30 AM XYZ", "soon"):
            with self.assertRaises(ManualInputError, msg=text):
                parse_clock(text)


class ParseWindowTests(unittest.TestCase):
    def test_bungie_tweet_example(self):
        off, on = parse_window("October 20", "8:30 AM PDT", "10:00 AM PDT", now=NOW)
        self.assertEqual(off, _utc(2026, 10, 20, 15, 30))   # PDT = UTC-7
        self.assertEqual(on, _utc(2026, 10, 20, 17, 0))

    def test_pst_is_fixed_offset(self):
        off, _ = parse_window("December 1", "8:00 AM PST", "9:00 AM PST", now=NOW)
        self.assertEqual(off, _utc(2026, 12, 1, 16, 0))     # PST = UTC-8

    def test_pt_follows_dst(self):
        summer, _ = parse_window("October 20", "8:00 AM", "9:00 AM", now=NOW)
        winter, _ = parse_window("December 1", "8:00 AM", "9:00 AM", now=NOW)
        self.assertEqual(summer, _utc(2026, 10, 20, 15, 0))
        self.assertEqual(winter, _utc(2026, 12, 1, 16, 0))

    def test_end_before_start_rolls_to_next_day(self):
        off, on = parse_window("October 20", "11:30 PM PDT", "1:00 AM PDT", now=NOW)
        self.assertEqual(on - off, 90 * 60)

    def test_year_rollover(self):
        now = datetime(2026, 12, 28, tzinfo=timezone.utc)
        off, _ = parse_window("January 6", "9:00 AM UTC", "10:00 AM UTC", now=now)
        self.assertEqual(off, _utc(2027, 1, 6, 9, 0))

    def test_recent_past_keeps_current_year(self):
        off, _ = parse_window("October 1", "9:00 AM UTC", "10:00 AM UTC", now=NOW)
        self.assertEqual(off, _utc(2026, 10, 1, 9, 0))

    def test_nonexistent_date(self):
        with self.assertRaises(ManualInputError):
            parse_window("February 30", "8:00 AM", "9:00 AM", now=NOW)


class BuildWindowTests(unittest.TestCase):
    def test_shape(self):
        w = build_manual_window(
            "destiny", "October 20", "8:30 AM PDT", "10:00 AM PDT", "  Update 1.0.6 ", now=NOW
        )
        self.assertEqual(w["event_type"], "Update 1.0.6")
        self.assertEqual(w["source"], "manual")
        self.assertEqual(w["game_label"], "Destiny 2")
        self.assertIn(f"<t:{w['offline_unix']}:t>", w["copy_text"])

    def test_empty_description(self):
        w = build_manual_window("marathon", "October 20", "8 AM", "9 AM", "", now=NOW)
        self.assertIsNone(w["event_type"])
        self.assertNotIn(":pencil:", w["copy_text"])


if __name__ == "__main__":
    unittest.main()
