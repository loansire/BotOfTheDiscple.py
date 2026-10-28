# -*- coding: utf-8 -*-
"""Cohérence du registre des topics avec /botconfig, /refresh et les publications."""
import unittest
from unittest import mock

from bot.discord.configbot.builder import NAV_TREE
from bot.publishing.registry import publications
from bot.topics import TOPICS


class RegistryTests(unittest.TestCase):
    def test_every_topic_is_reachable_in_botconfig(self):
        in_tree = [t for node in NAV_TREE.values() for t in node.get("topics", [])]
        self.assertEqual(sorted(in_tree), sorted(TOPICS))

    def test_publications_match_refreshable_topics(self):
        pubs = publications()
        self.assertTrue(set(pubs) <= set(TOPICS))
        self.assertEqual({k for k, t in TOPICS.items() if t.refresh}, set(pubs))

    def test_publication_interface(self):
        for key, pub in publications().items():
            for attr in ("on_added", "on_removed", "refresh"):
                with self.subTest(topic=key, attr=attr):
                    self.assertTrue(callable(getattr(pub, attr, None)))

    def test_rotation_topics_have_no_restore(self):
        # Les topics sans rôle sont édités en place : leur poll à la minute
        # répare déjà les messages, la pipeline ne doit pas les restaurer.
        for key, topic in TOPICS.items():
            if topic.no_role:
                self.assertFalse(hasattr(publications()[key], "restore"), key)


class RouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_changed_channels_trigger_hooks(self):
        from bot.publishing import router

        calls = []

        class Pub:
            def __init__(self, name):
                self.name = name

            async def on_added(self, bot, gid, info):
                calls.append(("added", self.name, info["channel_id"]))

            async def on_removed(self, bot, gid, info):
                calls.append(("removed", self.name, info["channel_id"]))

        pubs = {"a": Pub("a"), "b": Pub("b"), "c": Pub("c")}
        before = {"a": {"channel_id": "1"}, "b": {"channel_id": "2"}, "c": {"channel_id": None}}
        after = {"a": {"channel_id": "1"}, "b": {"channel_id": "3"}, "c": {"channel_id": "4"}}
        with mock.patch.object(router, "publications", lambda: pubs):
            await router.apply_config_change(None, "g", before, after)
        self.assertEqual(calls, [("removed", "b", "2"), ("added", "b", "3"), ("added", "c", "4")])


if __name__ == "__main__":
    unittest.main()
