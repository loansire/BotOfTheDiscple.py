# -*- coding: utf-8 -*-
from bot.core.config import RESOURCES_DIR
from bot.storage.static_data import wishes

WISHES_DIR = RESOURCES_DIR / "RivenWishes"
DEFAULT_IMAGE = "Default.webp"
THUMBNAIL_PATH = WISHES_DIR / "Lastwish.png"
FOOTER_ICON_PATH = RESOURCES_DIR / "footer_icon.png"


def load_wishes() -> list[dict]:
    """Vœux édités à la main en base (table compute_wish)."""
    return wishes()
