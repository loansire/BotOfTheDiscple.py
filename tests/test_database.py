# -*- coding: utf-8 -*-
"""Configuration des connexions : base de contenu (sans serveur)."""
import unittest
from unittest import mock

from bot.db import database


class ContentDbTests(unittest.TestCase):
    def tearDown(self):
        database.set_db(None)
        database.set_content_db(None)

    def test_content_db_is_separate_from_state(self):
        state, content = object(), object()
        database.set_db(state)
        self.assertIsNone(database.get_content_db())
        database.set_content_db(content)
        self.assertIs(database.get_content_db(), content)

    def test_content_config_reads_content_variables(self):
        with mock.patch.object(database.config, "CONTENT_DB_HOST", "db.example"):
            cfg = database.content_config()
        self.assertEqual((cfg.label, cfg.host), ("CONTENT_DB", "db.example"))


if __name__ == "__main__":
    unittest.main()
