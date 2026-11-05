# -*- coding: utf-8 -*-
"""Migrations du schéma : le bot crée et fait évoluer ses tables lui-même.

Chaque fichier `bot/db/migrations/NNNN_nom.sql` est appliqué UNE fois, dans
l'ordre de son numéro, puis noté dans `schema_migrations`. Pour faire évoluer
le schéma, on AJOUTE un fichier (on ne modifie jamais un fichier déjà appliqué).

Les fichiers contiennent des requêtes séparées par `;` en fin de ligne, sans
procédure stockée. En MySQL un CREATE/ALTER valide la transaction de lui-même :
une migration n'est donc pas atomique. D'où les `IF NOT EXISTS`, pour qu'une
migration interrompue puisse être rejouée sans erreur."""
from __future__ import annotations

import re
import warnings
from pathlib import Path

from bot.core.logger import log
from bot.db.database import Database

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_FILE_RE = re.compile(r"^(\d{4})_[\w-]+\.sql$")


def _statements(sql: str) -> list[str]:
    """Découpe un fichier en requêtes (commentaires `--` ignorés)."""
    lines = [line for line in sql.splitlines() if not line.lstrip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def pending_files(applied: set[int]) -> list[tuple[int, Path]]:
    files = []
    for path in MIGRATIONS_DIR.iterdir():
        match = _FILE_RE.match(path.name)
        if match and int(match.group(1)) not in applied:
            files.append((int(match.group(1)), path))
    return sorted(files)


async def migrate(db: Database) -> None:
    # « Table already exists » : simple note MySQL, attendue à chaque démarrage.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        await _create_migrations_table(db)
    applied = {row["version"] for row in await db.fetchall("SELECT version FROM schema_migrations")}
    for version, path in pending_files(applied):
        for statement in _statements(path.read_text(encoding="utf-8")):
            await db.execute(statement)
        await db.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)", (version, path.name)
        )
        log.info(f"[DB] Migration appliquée : {path.name}")


async def _create_migrations_table(db: Database) -> None:
    await db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INT UNSIGNED NOT NULL PRIMARY KEY,"
        " name VARCHAR(128) NOT NULL,"
        " applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )
