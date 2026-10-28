# -*- coding: utf-8 -*-
"""Chaque module du package s'importe (imports cassés, cycles) et chaque cog
déclaré expose setup()."""
import importlib
import pkgutil
import unittest

import bot


class ImportTests(unittest.TestCase):
    def test_all_modules_import(self):
        for info in pkgutil.walk_packages(bot.__path__, "bot."):
            with self.subTest(module=info.name):
                importlib.import_module(info.name)

    def test_cogs_have_setup(self):
        from bot.discord.commands import COGS

        for name in COGS:
            with self.subTest(cog=name):
                self.assertTrue(hasattr(importlib.import_module(name), "setup"))


if __name__ == "__main__":
    unittest.main()
