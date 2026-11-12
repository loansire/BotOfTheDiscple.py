# -*- coding: utf-8 -*-
"""Copie du contenu (content_*) de la base d'état vers la base de contenu
dédiée — À LANCER À LA MAIN, une fois, lors du passage à CONTENT_DB_*.

Usage :
    python -m scripts.copy_content
    (ou : python scripts/copy_content.py depuis la racine du projet)

Source : la base DB_* (où le contenu vivait jusqu'ici). Destination : la base
CONTENT_DB_* (schéma créé si besoin). Rejouable sans risque (INSERT IGNORE).
Ne supprime RIEN dans la source : les anciennes tables content_* de la base
d'état se suppriment à la main une fois la bascule validée.

Facultatif : le contenu se recalcule, mais la copie évite un trou entre la
bascule et le prochain calcul (maintenances, news déjà publiées)."""
import asyncio
import sys
from pathlib import Path

# Permet `python scripts/copy_content.py` depuis la racine.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db.database import Database, content_config, state_config  # noqa: E402
from bot.db.migrate import CONTENT, migrate  # noqa: E402

# Ordre : parents avant enfants (aucune contrainte de clé étrangère, mais une
# copie interrompue reste cohérente plus longtemps).
_TABLES = ("content_image", "content_post", "content_message", "content_component")


async def _copy_table(src: Database, dst: Database, table: str) -> int:
    rows = await src.fetchall(f"SELECT * FROM {table}")
    if not rows:
        return 0
    columns = list(rows[0])
    sql = (f"INSERT IGNORE INTO {table} ({', '.join(columns)})"
           f" VALUES ({', '.join(['%s'] * len(columns))})")
    if table == "content_image":
        # Une image à la fois : max_allowed_packet.
        for row in rows:
            await dst.execute(sql, tuple(row[c] for c in columns))
    else:
        async with dst.transaction() as cur:
            await cur.executemany(sql, [tuple(row[c] for c in columns) for row in rows])
    return len(rows)


async def main() -> int:
    cfg = content_config()
    if cfg is None:
        print("[ERREUR] CONTENT_DB_HOST absent du .env : aucune base de contenu dédiée.")
        return 1
    src = await Database.connect(state_config())
    dst = await Database.connect(cfg)
    try:
        await migrate(dst, CONTENT)
        for table in _TABLES:
            print(f"  {table:<20} {await _copy_table(src, dst, table):>6} ligne(s) lue(s)")
    finally:
        await dst.close()
        await src.close()
    print("\n✅ Copie terminée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
