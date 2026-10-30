# -*- coding: utf-8 -*-
"""Bandeaux d'activité : repli générique, flou dans le nom de cache, et
incrustation des icônes de l'Avant-garde (ombre, halo)."""
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from PIL import Image

from bot.features.vanguard import view
from bot.render import banner, image_cache

PLACEHOLDER = "/img/theme/destiny/bgs/pgcrs/placeholder.jpg"


def _jpeg(color: tuple[int, int, int], size=(1280, 720)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, format="JPEG")
    return out.getvalue()


def _png(color: tuple[int, int, int, int], size=(96, 96)) -> bytes:
    out = BytesIO()
    Image.new("RGBA", size, color).save(out, format="PNG")
    return out.getvalue()


class PlaceholderTests(unittest.TestCase):
    def test_empty_or_placeholder(self):
        self.assertTrue(banner.is_placeholder(None))
        self.assertTrue(banner.is_placeholder(""))
        self.assertTrue(banner.is_placeholder(PLACEHOLDER))

    def test_real_pgcr(self):
        self.assertFalse(banner.is_placeholder("/img/destiny_content/pgcr/tower.jpg"))

    def test_fallback_file_exists(self):
        self.assertTrue(banner.FALLBACK_BANNER.is_file())


class CacheNameTests(unittest.TestCase):
    def test_blur_in_cache_name(self):
        sharp = banner._cache_name("/a/b/raid.jpg", 3.25, 0.25, blur=0)
        blurred = banner._cache_name("/a/b/raid.jpg", 3.25, 0.25, blur=1)
        self.assertNotEqual(sharp, blurred)
        self.assertTrue(blurred.startswith("raid_"))


class GetBannerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.fallback = root / "fallback.jpg"
        self.fallback.write_bytes(_jpeg((255, 0, 0)))
        patches = [
            mock.patch.object(image_cache, "feature_dir", lambda feature: root / feature),
            mock.patch.object(banner, "FALLBACK_BANNER", self.fallback),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def _center(data: bytes) -> tuple[int, int, int]:
        img = Image.open(BytesIO(data)).convert("RGB")
        return img.getpixel((img.width // 2, img.height // 2))

    def _assert_red(self, data: bytes | None):
        self.assertIsNotNone(data)
        r, g, b = self._center(data)
        self.assertGreater(r, 200)
        self.assertLess(g + b, 60)

    async def test_placeholder_uses_fallback(self):
        with mock.patch.object(image_cache, "download", mock.AsyncMock()) as dl:
            data = await banner.get_banner(PLACEHOLDER, "test")
        dl.assert_not_called()
        self._assert_red(data)

    async def test_missing_path_uses_fallback(self):
        self._assert_red(await banner.get_banner(None, "test"))

    async def test_download_failure_uses_fallback(self):
        with mock.patch.object(image_cache, "download", mock.AsyncMock(return_value=None)):
            data = await banner.get_banner("/img/destiny_content/pgcr/raid.jpg", "test")
        self._assert_red(data)

    async def test_real_pgcr_is_used(self):
        blue = _jpeg((0, 0, 255))
        with mock.patch.object(image_cache, "download", mock.AsyncMock(return_value=blue)):
            data = await banner.get_banner("/img/destiny_content/pgcr/raid.jpg", "test")
        r, g, b = self._center(data)
        self.assertGreater(b, 200)
        self.assertLess(r + g, 60)
        w, h = Image.open(BytesIO(data)).size
        self.assertAlmostEqual(w / h, banner.BANNER_RATIO, delta=0.05)


class ComposeTests(unittest.TestCase):
    def setUp(self):
        self.banner = banner._crop(_jpeg((40, 40, 40)), banner.BANNER_RATIO, banner.BANNER_SCALE)
        self.icon = _png((128, 0, 128, 255))
        self.size = Image.open(BytesIO(self.banner)).size

    def _composed(self, color, grandmaster=False) -> Image.Image:
        out = view._compose(self.banner, [(self.icon, color)], grandmaster)
        return Image.open(BytesIO(out)).convert("RGB")

    def _just_outside_left(self, img: Image.Image) -> tuple[int, int, int]:
        """Pixel juste à gauche de l'icône, à mi-hauteur (zone du halo)."""
        h = img.height
        size = round(h * view._ICON_HEIGHT) + 2 * view._BORDER
        x = img.width - round(h * view._ICON_MARGIN) - size - 2
        return img.getpixel((x, h // 2))

    def test_size_preserved(self):
        self.assertEqual(self._composed(view._BORDER_COLOR).size, self.size)
        self.assertEqual(self._composed(view._BORDER_GOLD, grandmaster=True).size, self.size)

    def test_glow_only_for_colored_borders(self):
        plain = self._just_outside_left(self._composed(view._BORDER_COLOR))
        teal = self._just_outside_left(self._composed(view._BORDER_CHALLENGE))
        # Bordure claire : pas de halo (fond gris sombre, éventuellement ombré).
        self.assertLess(max(plain), 60)
        # Bordure défi : halo turquoise autour de l'icône.
        self.assertGreater(teal[1], plain[1] + 40)
        self.assertGreater(teal[2], plain[2] + 40)


if __name__ == "__main__":
    unittest.main()
