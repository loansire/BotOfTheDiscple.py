# -*- coding: utf-8 -*-
"""Modèle d'affichage et rendu générique (sans base ni réseau)."""
import unittest

import discord
from discord import ui

from bot.content.model import (
    EMBED,
    Component,
    Message,
    Post,
    button,
    image,
    image_id_of,
    separator,
    text,
)
from bot.render.components import image_ids, render

PNG = b"\x89PNG fake"


def _cv2_message() -> Message:
    return Message(accent_color=0xC27C0E, components=[
        text("# Ada-1"),
        separator(),
        image("section", PNG, "ada_1.webp", text="**Item**\n<:Glimer:1> x25000"),
        image("gallery", PNG, "banner.webp"),
        button("Rotation", "rotation:raid", emoji="🗓️", style="primary"),
        button("Autre", "rotation:dungeon"),
    ])


class ModelTests(unittest.TestCase):
    def test_hash_covers_everything_but_not_image_bytes_twice(self):
        a = Post("ada", "repost", {"default": [_cv2_message()]})
        b = Post("ada", "repost", {"default": [_cv2_message()]})
        self.assertEqual(a.content_hash(), b.content_hash())
        b.messages[0].components[2].text = "**Item**\n<:Glimer:1> x30000"  # coût changé
        self.assertNotEqual(a.content_hash(), b.content_hash())

    def test_images_are_deduplicated_by_content(self):
        post = Post("ada", "repost", {"default": [_cv2_message()]})
        self.assertEqual(list(post.images()), [image_id_of(PNG)])
        self.assertNotIn("image_data", post.messages[0].components[2].row())


class RenderCv2Tests(unittest.TestCase):
    def test_each_component_maps_to_one_discord_item(self):
        msg = _cv2_message()
        out = render(msg, {image_id_of(PNG): PNG})
        container = out.view.children[0]
        self.assertIsInstance(container, ui.Container)
        kinds = [type(i).__name__ for i in container.children]
        self.assertEqual(kinds, ["TextDisplay", "Separator", "Section", "MediaGallery", "ActionRow"])
        self.assertEqual(container.children[0].content, "# Ada-1")
        row = container.children[4]
        self.assertEqual([b.custom_id for b in row.children], ["rotation:raid", "rotation:dungeon"])
        self.assertEqual(sorted(f.filename for f in out.files), ["ada_1.webp", "banner.webp"])

    def test_missing_image_degrades_without_crash(self):
        out = render(_cv2_message(), {})
        kinds = [type(i).__name__ for i in out.view.children[0].children]
        self.assertEqual(kinds, ["TextDisplay", "Separator", "TextDisplay", "ActionRow"])
        self.assertEqual(out.files, [])

    def test_files_are_fresh_each_render(self):
        images = {image_id_of(PNG): PNG}
        a, b = render(_cv2_message(), images), render(_cv2_message(), images)
        self.assertIsNot(a.files[0], b.files[0])


class RenderEmbedTests(unittest.TestCase):
    def test_embed_fields_and_buttons(self):
        msg = Message(layout=EMBED, accent_color=0xFF0000, components=[
            Component("embed_author", title="@help.bungie.net", url="https://help.bungie.net",
                      image_url="https://cdn.discordapp.com/emojis/1.png"),
            Component("embed_description", text="## [Infos](https://x)"),
            Component("embed_field", title=":x: Stop", text="<t:1:t>", inline_field=True),
            image("embed_thumbnail", PNG, "thumb.png", mime="image/png"),
            Component("embed_footer", text="BotOfTheDisciple • 2026/11/05 10:00"),
            button("Copier les infos", "maintenance:copy:3", emoji="💾", style="primary"),
        ])
        out = render(msg, {image_id_of(PNG): PNG})
        self.assertIsInstance(out.embed, discord.Embed)
        self.assertEqual(out.embed.author.icon_url, "https://cdn.discordapp.com/emojis/1.png")
        self.assertEqual(out.embed.fields[0].name, ":x: Stop")
        self.assertTrue(out.embed.fields[0].inline)
        self.assertEqual(out.embed.thumbnail.url, "attachment://thumb.png")
        self.assertEqual(out.view.children[0].custom_id, "maintenance:copy:3")
        self.assertEqual(image_ids(msg), {image_id_of(PNG)})

    def test_select_groups_following_options(self):
        msg = Message(layout=EMBED, components=[
            Component("embed_description", text="## Wishwall"),
            Component("select", title="Sélectionnez un vœu...", btn_action="wishwall:select"),
            Component("option", btn_label="1️⃣ - Clé", btn_action="0"),
            Component("option", btn_label="2️⃣ - Coffre", btn_action="1"),
        ])
        out = render(msg, {})
        select = out.view.children[0]
        self.assertIsInstance(select, ui.Select)
        self.assertEqual([o.value for o in select.options], ["0", "1"])


if __name__ == "__main__":
    unittest.main()
