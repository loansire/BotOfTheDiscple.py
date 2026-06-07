# -*- coding: utf-8 -*-
import json

import discord

from bot.config import RESOURCES_DIR

WISHES_DIR = RESOURCES_DIR / "RivenWishes"
WISHES_JSON = WISHES_DIR / "wishes.json"
DEFAULT_IMAGE = "Default.webp"
THUMBNAIL_PATH = WISHES_DIR / "Lastwish.png"
FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"


def load_wishes() -> list[dict]:
    with open(WISHES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)["voeux"]


def load_image(file_name: str) -> discord.File:
    """Charge l'image du vœu, ou l'image par défaut si absente."""
    path = WISHES_DIR / file_name
    if path.is_file():
        return discord.File(path, filename=file_name)
    return discord.File(WISHES_DIR / DEFAULT_IMAGE, filename=DEFAULT_IMAGE)


def _make_file(path, filename: str) -> discord.File | None:
    return discord.File(path, filename=filename) if path.is_file() else None


def fresh_files(image_name: str) -> list[discord.File]:
    """Renvoie des File NEUFS (un discord.File est consommé après un envoi)."""
    files = [
        load_image(image_name),
        _make_file(THUMBNAIL_PATH, "thumbnail.png"),
        _make_file(FOOTER_ICON_PATH, "footer_icon.png"),
    ]
    return [f for f in files if f]