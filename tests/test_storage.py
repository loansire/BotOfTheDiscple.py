# -*- coding: utf-8 -*-
"""Stores SQL : sémantique en mémoire, requêtes écrites, chargement, import
des anciens fichiers JSON."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bot.db import database
from bot.db.migrate import _statements, pending_files
from bot.features.xur.state import XurMessageState
from bot.storage import base, legacy_import
from bot.storage.compute_state import compute_state
from bot.storage.messages import MultiMessageState, SingleMessageState, messages
from bot.storage.pipeline_state import PipelineState
from bot.storage.static_data import parse_positions, static_data
from bot.storage.subscriptions import (
    iter_subscribers,
    load_config_state,
    set_topic_destination,
)
from tests.storage_helpers import RecordingDatabase, reset_memory


class _Base(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        reset_memory()

    def use_db(self, db):
        database.set_db(db)
        self.addCleanup(database.set_db, None)
        return db


class MessageStateTests(_Base):
    def test_multi_semantics(self):
        st = MultiMessageState("ada")
        self.assertEqual(st.get("1"), {"message_ids": [], "hash": ""})
        st.set("1", message_ids=[10, "11"], content_hash="h")
        st.set("1", content_hash="h2")  # ids conservés
        self.assertEqual(st.get(1), {"message_ids": ["10", "11"], "hash": "h2"})
        self.assertEqual(list(st.iter_guilds()), [("1", {"message_ids": ["10", "11"], "hash": "h2"})])
        st.purge("1")
        self.assertEqual(st.get("1")["message_ids"], [])

    async def test_invalidate_keeps_ids_and_is_per_topic(self):
        a, b = MultiMessageState("ada"), MultiMessageState("eververse")
        a.set("1", message_ids=["10"], content_hash="h")
        b.set("1", message_ids=["20"], content_hash="h")
        await a.invalidate()
        self.assertEqual(a.get("1"), {"message_ids": ["10"], "hash": ""})
        self.assertEqual(b.get("1")["hash"], "h")

    async def test_single_semantics(self):
        st = SingleMessageState("distortion")
        self.assertEqual(st.get("1"), {"message_id": None, "hash": None})
        st.set("1", message_id=5, content_hash="h")
        st.set("2", message_id=6, content_hash="h")
        await st.invalidate()
        st.purge("2")
        self.assertEqual(st.get("1"), {"message_id": "5", "hash": None})
        self.assertEqual(st.get("2"), {"message_id": None, "hash": None})

    def test_xur_slots(self):
        st = XurMessageState()
        st.set("1", status_id="7", category_ids=["8", "9"], content_hash="h")
        st.clear_categories("1")
        self.assertEqual(st.get("1"), {"status_id": "7", "category_ids": [], "hash": "h"})
        self.assertEqual(messages.get("1", "xur").slots, {"content": [], "status": ["7"]})


class FlushTests(_Base):
    async def test_message_rows_written_in_order(self):
        db = self.use_db(RecordingDatabase())
        st = MultiMessageState("ada")
        st.set("1", message_ids=["10", "11"], content_hash="h")
        await st.save()
        sqls = [sql.split(" (")[0] for sql, _ in db.writes]
        self.assertEqual(
            sqls,
            [
                "DELETE FROM bot_message WHERE bot_id = %s AND guild_id = %s AND topic = %s",
                "INSERT INTO bot_publication",
                "INSERT INTO bot_message",
                "INSERT INTO bot_message",
            ],
        )
        self.assertEqual(db.writes[2][1], ("live", 1, "ada", "content", 0, 10))
        self.assertEqual(db.writes[3][1], ("live", 1, "ada", "content", 1, 11))

        db.writes.clear()
        st.purge("1")
        await st.save()
        self.assertTrue(db.writes[-1][0].startswith("DELETE FROM bot_publication"))

        db.writes.clear()
        await st.save()  # rien de sale → aucune requête
        self.assertEqual(db.writes, [])

    async def test_failed_write_keeps_changes_pending(self):
        db = self.use_db(RecordingDatabase(fail=True))
        compute_state.set("pipeline.last_reset", "x")
        with self.assertRaises(ConnectionError):
            await base.flush()
        db.fail = False
        await base.flush()
        self.assertEqual(
            db.writes[0][1], ("pipeline.last_reset", json.dumps("x"))
        )

    async def test_subscription_rows(self):
        db = self.use_db(RecordingDatabase())
        await set_topic_destination("xur", "1", "11", is_thread=True, role_id="5", guild_name="G")
        self.assertEqual(db.writes[1][1], ("live", 1, "xur", 11, 1, 5, "G", None))
        self.assertEqual(
            load_config_state("1")["xur"], {"channel_id": "11", "is_thread": True, "role_id": "5"}
        )
        await set_topic_destination("xur", "1", None)
        self.assertEqual(list(iter_subscribers("xur")), [])
        self.assertEqual(len(db.writes), 3)  # 2e écriture : DELETE seul


class LoadTests(_Base):
    async def test_load_rebuilds_memory(self):
        db = RecordingDatabase({
            "FROM bot_publication": [{"guild_id": 1, "topic": "ada", "content_hash": "h"}],
            "FROM bot_message": [
                {"guild_id": 1, "topic": "ada", "slot": "content", "message_id": 10},
                {"guild_id": 1, "topic": "xur", "slot": "status", "message_id": 7},
            ],
            "FROM bot_subscription": [{
                "guild_id": 1, "topic": "ada", "channel_id": 11, "is_thread": 0,
                "role_id": None, "guild_name": "G", "channel_name": "c",
            }],
            "FROM compute_state": [{"name": "pipeline.last_reset", "value": '"2026-10-28"'}],
            "FROM compute_loot_table_item": [{"activity_key": "rappel", "item_hash": 42}],
            "FROM compute_loot_table": [
                {"activity_key": "rappel", "label": "Rappel", "banner_file": "r.png", "type": "prestige"}
            ],
            "FROM compute_vendor_whitelist": [{"category": "armor", "positions": "1, 2,x"}],
        })
        self.use_db(db)
        await base.load_all()
        self.assertEqual(MultiMessageState("ada").get("1"), {"message_ids": ["10"], "hash": "h"})
        self.assertEqual(XurMessageState().status_id("1"), "7")
        self.assertEqual(list(iter_subscribers("ada")), [("1", "11", {"name": "c", "is_thread": False, "role": None})])
        self.assertEqual(PipelineState().last_reset_iso, "2026-10-28")
        self.assertEqual(static_data.loot_tables["rappel"]["items"], [42])
        self.assertEqual(static_data.vendor_whitelist, {"armor": [1, 2]})

    def test_parse_positions(self):
        self.assertEqual(parse_positions(""), [])
        self.assertEqual(parse_positions("2,3; 4"), [2, 3, 4])


class LegacyImportTests(_Base):
    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        for name in ("ALERTS_DIR", "TOKENS"):
            target = self.dir if name == "ALERTS_DIR" else self.dir / "bungie_tokens.json"
            patcher = mock.patch.object(legacy_import, name, target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def write(self, name, data):
        (self.dir / name).write_text(json.dumps(data), encoding="utf-8")

    def test_states_are_converted(self):
        self.write("ada_messages.json", {"guilds": {"1": {"message_ids": ["10"], "hash": "h"}}})
        self.write("distortion_state.json", {"1": {"message_id": "5", "hash": None}})
        self.write("weekly_messages.json", {
            "guilds": {"1": {
                "weekly_raid": {"message_id": "20", "hash": "r"},
                "daily_vanguard": {"message_ids": ["30", "31"], "hash": "v"},
            }},
            "signatures": {"weekly_raid": {"period": "p", "sig": ["a"]}},
            "vanguard_challenges": {"week": "w", "items": {"1": 2}},
        })
        self.write("xur_messages.json", {"guilds": {"1": {"message_ids": ["7", "8"], "hash": ""}}})
        self.write("pipeline_state.json", {"last_reset": "2026-10-28T17:00:00+00:00"})
        self.write("news_state.json", {"twid": "blt1"})
        self.write("subscriptions.json", {"1": {"name": "G", "topics": {"ada": {"11": {"is_thread": False, "role": None}}}}})

        done = legacy_import._import_states()

        self.assertIn("weekly_messages.json", done)
        self.assertEqual(MultiMessageState("ada").get("1"), {"message_ids": ["10"], "hash": "h"})
        self.assertEqual(SingleMessageState("distortion").get("1"), {"message_id": "5", "hash": None})
        self.assertEqual(SingleMessageState("weekly_raid").get("1"), {"message_id": "20", "hash": "r"})
        self.assertEqual(MultiMessageState("daily_vanguard").get("1")["message_ids"], ["30", "31"])
        self.assertEqual(XurMessageState().get("1"), {"status_id": "7", "category_ids": ["8"], "hash": ""})
        self.assertEqual(compute_state.get("weekly.signature.weekly_raid"), {"period": "p", "sig": ["a"]})
        self.assertEqual(compute_state.get("weekly.vanguard_challenges"), {"week": "w", "items": {"1": 2}})
        self.assertEqual(PipelineState().last_reset_iso, "2026-10-28T17:00:00+00:00")
        self.assertEqual(compute_state.get("news.last_id.twid"), "blt1")
        self.assertEqual(len(list(iter_subscribers("ada"))), 1)

    async def test_import_runs_once(self):
        db = self.use_db(RecordingDatabase())
        self.write("news_state.json", {"twid": "blt1"})
        with mock.patch.object(legacy_import, "_import_static", mock.AsyncMock(return_value=[])):
            await legacy_import.import_legacy_json()
            self.assertTrue(compute_state.get(legacy_import.DONE_KEY))
            compute_state.delete("news.last_id.twid")
            await legacy_import.import_legacy_json()
        self.assertIsNone(compute_state.get("news.last_id.twid"))
        self.assertTrue(db.writes)


class MigrationFileTests(unittest.TestCase):
    def test_files_split_into_statements(self):
        files = pending_files(set())
        self.assertEqual(files[0][0], 1)
        for _, path in files:
            statements = _statements(path.read_text(encoding="utf-8"))
            self.assertTrue(statements)
            for sql in statements:
                self.assertTrue(sql.startswith("CREATE TABLE IF NOT EXISTS"), sql[:60])
                self.assertNotIn("--", sql)


if __name__ == "__main__":
    unittest.main()
