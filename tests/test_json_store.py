# -*- coding: utf-8 -*-
"""États JSON persistés : formats sur disque (à ne PAS casser), purge, invalidation."""
import json
import tempfile
import unittest
from pathlib import Path

from bot.storage.json_store import MultiMessageState, SingleMessageState


class _TmpDir(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def read(self, name):
        return json.loads((self.dir / name).read_text(encoding="utf-8"))


class MultiMessageStateTests(_TmpDir):
    def test_roundtrip_and_disk_format(self):
        st = MultiMessageState(self.dir / "m.json")
        st.set("1", message_ids=["10", "11"], content_hash="h")
        st.save()
        self.assertEqual(
            self.read("m.json"), {"guilds": {"1": {"message_ids": ["10", "11"], "hash": "h"}}}
        )
        again = MultiMessageState(self.dir / "m.json")
        self.assertEqual(again.get(1), {"message_ids": ["10", "11"], "hash": "h"})

    def test_invalidate_keeps_ids(self):
        st = MultiMessageState(self.dir / "m.json")
        st.set("1", message_ids=["10"], content_hash="h")
        st.invalidate()
        self.assertEqual(st.get("1"), {"message_ids": ["10"], "hash": ""})

    def test_obsolete_key_and_corrupted_file(self):
        (self.dir / "m.json").write_text('{"last_reset": "x", "guilds": {}}', encoding="utf-8")
        self.assertNotIn("last_reset", MultiMessageState(self.dir / "m.json")._data)
        (self.dir / "bad.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(MultiMessageState(self.dir / "bad.json")._data, {})


class SingleMessageStateTests(_TmpDir):
    def test_roundtrip_purge_invalidate(self):
        st = SingleMessageState(self.dir / "s.json")
        self.assertEqual(st.get("1"), {"message_id": None, "hash": None})
        st.set("1", message_id=5, content_hash="h")
        st.set("2", message_id=6, content_hash="h")
        st.invalidate()
        st.purge("2")
        st.save()
        self.assertEqual(self.read("s.json"), {"1": {"message_id": "5", "hash": None}})


if __name__ == "__main__":
    unittest.main()
