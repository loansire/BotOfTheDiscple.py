# -*- coding: utf-8 -*-
"""Configuration des connexions : base de contenu (sans serveur)."""
import unittest
from unittest import mock

from bot.db import database


class ContentDbTests(unittest.TestCase):
    def tearDown(self):
        database.set_db(None)
        database.set_content_db(None)

    def test_falls_back_to_state_db(self):
        state = object()
        database.set_db(state)
        self.assertIs(database.get_content_db(), state)
        self.assertFalse(database.has_content_db())

    def test_dedicated_content_db(self):
        state, content = object(), object()
        database.set_db(state)
        database.set_content_db(content)
        self.assertIs(database.get_content_db(), content)
        self.assertTrue(database.has_content_db())

    def test_content_config_optional(self):
        with mock.patch.object(database.config, "CONTENT_DB_HOST", None):
            self.assertIsNone(database.content_config())
        with mock.patch.object(database.config, "CONTENT_DB_HOST", "db.example"):
            self.assertEqual(database.content_config().label, "CONTENT_DB")


if __name__ == "__main__":
    unittest.main()
