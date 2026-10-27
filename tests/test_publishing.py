# -*- coding: utf-8 -*-
"""Moteurs de publication (repost multi-message, mono-message) sur faux Discord."""
import tempfile
import unittest
from pathlib import Path

from bot.features.weekly.state import TopicSlot, WeeklyMessageState
from bot.publishing.repost import Payload, RepostTopic
from bot.publishing.single import SingleTopic
from bot.storage.json_store import MultiMessageState
from tests.fake_discord import FakeBot, FakeChannel, FakeGuild, FakeView, subscriptions

TOPIC = "demo"


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.ch1, self.ch2 = FakeChannel(11), FakeChannel(22)
        self.bot = FakeBot([FakeGuild(1, {11: self.ch1}), FakeGuild(2, {22: self.ch2})])
        self.subs = {"1": ("11", "role1"), "2": ("22", None)}
        self.version = "v1"
        self.fetches = 0
        self.purges = 0

    def tearDown(self):
        self._tmp.cleanup()

    async def _payload(self, strict):
        self.fetches += 1
        return Payload(self.version, f"h-{self.version}", [self.version])

    async def _views(self, data):
        return [(FakeView(f"{data}-a"), []), (FakeView(f"{data}-b"), [])]


class RepostTopicTests(_Base):
    def make(self, state):
        return RepostTopic(
            topic=TOPIC, tag="Demo", state=lambda: state, payload=self._payload,
            build_views=self._views, purge_cache=self._purge,
        )

    def _purge(self):
        self.purges += 1

    async def test_publish_skip_and_change(self):
        state = MultiMessageState(self.dir / "m.json")
        pub = self.make(state)
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
            # 2 vues + ping (rôle défini) / 2 vues sans ping.
            self.assertEqual(len(self.ch1.messages), 3)
            self.assertEqual(self.ch1.pings, ["<@&role1>"])
            self.assertEqual(len(self.ch2.messages), 2)
            first_ids = state.get("1")["message_ids"]

            await pub.publish(self.bot)  # même hash → rien ne bouge
            self.assertEqual(state.get("1")["message_ids"], first_ids)

            self.version = "v2"
            await pub.publish(self.bot)  # nouveau contenu → anciens supprimés
            self.assertEqual(len(self.ch1.messages), 3)
            self.assertTrue(set(first_ids).isdisjoint(state.get("1")["message_ids"]))
            self.assertEqual(self.purges, 3)

    async def test_restore_lazy_and_without_ping(self):
        state = MultiMessageState(self.dir / "m.json")
        pub = self.make(state)
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
            self.fetches = 0
            await pub.restore(self.bot)
            self.assertEqual(self.fetches, 0)  # rien ne manque → aucun fetch

            await self.ch1.messages[int(state.get("1")["message_ids"][0])].delete()
            await pub.restore(self.bot)
            self.assertEqual(self.fetches, 1)
            self.assertEqual(len(self.ch1.messages), 2)  # reconstruit, sans ping
            self.assertEqual(self.ch1.pings, [])
            self.assertEqual(self.purges, 1)  # restore ne purge pas

    async def test_refresh_reposts_without_ping(self):
        state = MultiMessageState(self.dir / "m.json")
        pub = self.make(state)
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
            await pub.refresh(self.bot)
            self.assertEqual(len(self.ch1.messages), 2)
            self.assertEqual(self.ch1.pings, [])

    async def test_added_and_removed(self):
        state = MultiMessageState(self.dir / "m.json")
        pub = self.make(state)
        info = {"channel_id": "11", "is_thread": False, "role_id": "r"}
        with subscriptions(TOPIC, {}):
            await pub.on_added(self.bot, "1", info)
            self.assertEqual(self.ch1.pings, ["<@&r>"])
            await pub.on_removed(self.bot, "1", info)
            self.assertEqual(self.ch1.messages, {})
            self.assertFalse(state.get("1")["message_ids"])

    async def test_partial_send_clears_hash(self):
        state = MultiMessageState(self.dir / "m.json")
        pub = self.make(state)
        original = self.ch2.send
        calls = {"n": 0}

        async def flaky(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 2:
                import discord
                raise discord.DiscordException("boom")
            return await original(*args, **kwargs)

        self.ch2.send = flaky
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
        self.assertEqual(state.get("2")["hash"], "")
        self.assertEqual(state.get("1")["hash"], "h-v1")

    async def test_weekly_topic_slot_keeps_file_format(self):
        weekly = WeeklyMessageState(self.dir / "w.json")
        weekly.set("1", TOPIC, message_id="999", content_hash="old")  # ancien format
        pub = self.make(TopicSlot(weekly, TOPIC))
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
        entry = weekly.get("1", TOPIC)
        self.assertEqual(set(entry), {"message_ids", "hash"})
        self.assertEqual(len(entry["message_ids"]), 3)


class SingleTopicTests(_Base):
    async def _view(self, data):
        return FakeView(data), []

    def make(self, state):
        return SingleTopic(topic=TOPIC, state=lambda: state, payload=self._payload, build_view=self._view)

    async def test_publish_restore_refresh(self):
        weekly = WeeklyMessageState(self.dir / "w.json")
        pub = self.make(weekly)
        with subscriptions(TOPIC, self.subs):
            await pub.publish(self.bot)
            mid = weekly.get("1", TOPIC)["message_id"]
            self.assertEqual(len(self.ch1.messages), 1)
            self.assertEqual(len(self.ch1.messages[int(mid)].view.items), 1)  # ping injecté

            await pub.publish(self.bot)
            self.assertEqual(weekly.get("1", TOPIC)["message_id"], mid)

            await self.ch1.messages[int(mid)].delete()
            await pub.restore(self.bot)
            self.assertEqual(len(self.ch1.messages), 1)
            self.assertNotEqual(weekly.get("1", TOPIC)["message_id"], mid)

            await pub.refresh(self.bot)
            self.assertEqual(len(self.ch1.messages), 1)


if __name__ == "__main__":
    unittest.main()
