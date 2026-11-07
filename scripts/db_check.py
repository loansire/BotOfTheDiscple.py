# -*- coding: utf-8 -*-
"""Vérification de la base — À LANCER À LA MAIN après avoir rempli le .env.

Usage :
    python -m scripts.db_check
    (ou : python scripts/db_check.py depuis la racine du projet)

Se connecte avec les variables DB_* du .env, applique les migrations en
attente, puis affiche le nombre de lignes de chaque table. N'envoie RIEN sur
Discord. Utile pour valider l'accès à la base partagée (installation d'un
nouveau bot, changement d'hébergeur) sans démarrer le bot."""
import asyncio
import sys
from pathlib import Path

# Permet `python scripts/db_check.py` depuis la racine.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.db.database import get_db  # noqa: E402
from bot.storage import close_storage, open_storage  # noqa: E402


async def main() -> int:
    try:
        await open_storage()
    except Exception as e:
        print(f"[ERREUR] Connexion / migration impossible : {e!r}")
        return 1
    try:
        db = get_db()
        version = (await db.fetchall("SELECT VERSION() AS v"))[0]["v"]
        print(f"Serveur : {version}\n")
        for row in await db.fetchall("SHOW TABLES"):
            table = next(iter(row.values()))
            count = (await db.fetchall(f"SELECT COUNT(*) AS n FROM `{table}`"))[0]["n"]
            print(f"  {table:<28} {count:>6} ligne(s)")
    finally:
        await close_storage()
    print("\n✅ Base opérationnelle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
