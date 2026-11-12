# -*- coding: utf-8 -*-
"""Migrations du schéma : le bot crée et fait évoluer ses tables lui-même.

Deux jeux de migrations, un par base (cf. bot/db/database.py) :
- `migrations/state/`   : base d'état, suivi dans `schema_migrations` ;
- `migrations/content/` : base de contenu, suivi dans
  `content_schema_migrations`. Seul le bot qui ÉCRIT le contenu (live) les
  applique ; un bot qui ne fait que lire (lite) ne touche pas à ce schéma.
Deux tables de suivi distinctes : les deux jeux peuvent cohabiter dans une
même base (pas de base de contenu dédiée) sans que leurs numéros se mélangent.

Chaque fichier `NNNN_nom.sql` est appliqué UNE fois, dans l'ordre de son
numéro, puis noté dans la table de suivi. Pour faire évoluer le schéma, on
AJOUTE un fichier (on ne modifie jamais un fichier déjà appliqué).

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
STATE = "state"
CONTENT = "content"
_TRACKING_TABLES = {STATE: "schema_migrations", CONTENT: "content_schema_migrations"}

_FILE_RE = re.compile(r"^(\d{4})_[\w-]+\.sql$")


def _statements(sql: str) -> list[str]:
    """Découpe un fichier en requêtes (commentaires `--` ignorés)."""
    lines = [line for line in sql.splitlines() if not line.lstrip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def pending_files(applied: set[int], kind: str = STATE) -> list[tuple[int, Path]]:
    files = []
    for path in (MIGRATIONS_DIR / kind).iterdir():
        match = _FILE_RE.match(path.name)
        if match and int(match.group(1)) not in applied:
            files.append((int(match.group(1)), path))
    return sorted(files)


async def migrate(db: Database, kind: str = STATE) -> None:
    table = _TRACKING_TABLES[kind]
    # « Table already exists » : simple note MySQL, attendue à chaque démarrage.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        await _create_migrations_table(db, table)
    applied = {row["version"] for row in await db.fetchall(f"SELECT version FROM {table}")}
    for version, path in pending_files(applied, kind):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for statement in _statements(path.read_text(encoding="utf-8")):
                await db.execute(statement)
        await db.execute(
            f"INSERT INTO {table} (version, name) VALUES (%s, %s)", (version, path.name)
        )
        log.info(f"[DB] Migration {kind} appliquée : {path.name}")


async def _create_migrations_table(db: Database, table: str) -> None:
    await db.execute(
        f"CREATE TABLE IF NOT EXISTS {table} ("
        " version INT UNSIGNED NOT NULL PRIMARY KEY,"
        " name VARCHAR(128) NOT NULL,"
        " applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )
