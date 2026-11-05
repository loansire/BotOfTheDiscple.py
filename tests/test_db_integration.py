# -*- coding: utf-8 -*-
"""Aller-retour RÉEL avec la base du .env (à lancer sur une base de TEST).

Ignoré par défaut. Pour l'activer :
    BOTD_DB_TESTS=1 python -m unittest tests.test_db_integration

N'utilise que des topics préfixés `test:` et les supprime à la fin."""
import os
import unittest
from datetime import datetime, timedelta, timezone

from bot.content import store
from bot.content.model import EMBED, Component, Message, Post, button, image, image_id_of, separator, text
from bot.db.database import close_db, get_db, init_db
from bot.db.migrate import migrate
from bot.render.components import render

TOPIC = "test:integration"
PNG = b"\x89PNG integration " + os.urandom(8)


def _post(cost: str) -> Post:
    return Post(TOPIC, "repost", {
        "default": [Message(accent_color=0xC27C0E, components=[
            text("# Ada-1 ✨"),
            separator(),
            image("section", PNG, "ada_1.webp", text=f"**Item**\n<:Glimer:1> x{cost}"),
            button("Rotation", "rotation:raid", emoji="🗓️", style="primary"),
        ])],
        "fr": [Message(layout=EMBED, components=[Component("embed_description", text="## FR")])],
    })


@unittest.skipUnless(os.getenv("BOTD_DB_TESTS") == "1", "base de test non demandée")
class ContentStoreIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        db = await init_db()
        await migrate(db)
        await self._cleanup()

    async def asyncTearDown(self):
        await self._cleanup()
        await close_db()

    async def _cleanup(self):
        db = get_db()
        for table in ("content_component", "content_message", "content_post"):
            await db.execute(f"DELETE FROM {table} WHERE topic LIKE 'test:%%'")
        await db.execute("DELETE FROM content_image WHERE image_id = %s", (image_id_of(PNG),))
        store._post_cache.clear()
        store._image_cache.clear()

    async def test_versioned_roundtrip(self):
        v1, written = await store.save_post(_post("25000"))
        self.assertEqual((v1, written), (1, True))
        self.assertEqual(await store.save_post(_post("25000")), (1, False))  # inchangé
        v2, written = await store.save_post(_post("30000"))
        self.assertEqual((v2, written), (2, True))

        headers = await store.latest_headers()
        self.assertEqual(headers[TOPIC].version, 2)

        loaded = await store.load_post(TOPIC)
        self.assertEqual(loaded.content_hash(), _post("30000").content_hash())
        self.assertEqual(loaded.variants["fr"][0].components[0].text, "## FR")
        section = loaded.messages[0].components[2]
        self.assertEqual(section.text, "**Item**\n<:Glimer:1> x30000")

        images = await store.load_images([section.image_id])
        self.assertEqual(images[section.image_id], PNG)
        out = render(loaded.messages[0], images)
        self.assertEqual([f.filename for f in out.files], ["ada_1.webp"])

        old = await store.load_post(TOPIC, 1)
        self.assertIn("x25000", old.messages[0].components[2].text)

        # Purge à J+8 : la v1 disparaît, la v2 (dernière) et son image restent.
        store._post_cache.clear()
        store._image_cache.clear()
        await store.prune(datetime.now(timezone.utc) + timedelta(days=8))
        self.assertIsNone(await store.load_post(TOPIC, 1))
        self.assertIsNotNone(await store.load_post(TOPIC, 2))
        self.assertEqual(await store.load_images([section.image_id]), {section.image_id: PNG})


if __name__ == "__main__":
    unittest.main()
