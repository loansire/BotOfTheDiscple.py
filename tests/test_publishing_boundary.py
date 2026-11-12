# -*- coding: utf-8 -*-
"""Frontière publication / calcul.

Le bot lite (repo séparé) reprend TELS QUELS, aux mêmes chemins, les modules
de PUBLISHING_SIDE : un correctif fait ici s'y reporte par
`git format-patch … -- <ces chemins> | git am -3`. Ces modules ne doivent donc
importer que d'autres modules de cette liste : jamais bot.features,
bot.bungie, bot.compute ni les cogs du live.

Ajouter un module à la liste = il part aussi dans le lite."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Chemins (relatifs à la racine) copiés dans le lite. Un dossier = tous ses .py.
PUBLISHING_SIDE = (
    "bot/__init__.py",
    "bot/topics.py",
    "bot/core/__init__.py",
    "bot/core/aio.py",
    "bot/core/http.py",
    "bot/core/jsonio.py",
    "bot/core/logger.py",
    "bot/core/reset.py",
    "bot/core/rotation.py",
    "bot/db",
    "bot/content",
    "bot/publishing",
    "bot/render/__init__.py",
    "bot/render/components.py",
    "bot/render/embed.py",
    "bot/render/emotes.py",
    "bot/render/layout.py",
    "bot/storage/base.py",
    "bot/storage/messages.py",
    "bot/storage/subscriptions.py",
    "bot/discord/__init__.py",
    "bot/discord/configbot",
    "bot/discord/cogs/__init__.py",
    "bot/discord/cogs/configbot.py",
    "bot/discord/cogs/content_actions.py",
)

# Propres à chaque bot (même nom, contenu différent dans le lite) : on peut
# les importer, ils ne sont pas copiés. config : variables du .env de chaque
# bot ; bot.storage (__init__) : ouverture des bases et migrations.
PER_BOT = {"bot.core.config", "bot.storage"}


def _files() -> list[Path]:
    out = []
    for rel in PUBLISHING_SIDE:
        path = ROOT / rel
        out.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
    return out


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _is_module(name: str) -> bool:
    base = ROOT.joinpath(*name.split("."))
    return base.with_suffix(".py").exists() or (base / "__init__.py").exists()


def _imports(path: Path) -> set[str]:
    """Modules `bot.*` importés (y compris dans les fonctions)."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith("bot"))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").startswith("bot"):
            for alias in node.names:
                sub = f"{node.module}.{alias.name}"
                found.add(sub if _is_module(sub) else node.module)
    return found


class PublishingBoundaryTests(unittest.TestCase):
    def test_paths_exist(self):
        for rel in PUBLISHING_SIDE:
            with self.subTest(path=rel):
                self.assertTrue((ROOT / rel).exists())

    def test_publishing_side_is_self_contained(self):
        allowed = {_module_name(p) for p in _files()} | PER_BOT
        for path in _files():
            for name in sorted(_imports(path)):
                with self.subTest(module=_module_name(path), imports=name):
                    self.assertIn(name, allowed)


if __name__ == "__main__":
    unittest.main()
