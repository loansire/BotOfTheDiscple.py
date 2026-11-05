# -*- coding: utf-8 -*-
"""Connexion MySQL / MariaDB partagée par tout le bot (pool aiomysql).

Un seul pool, ouvert au démarrage (cf. Main.py) et fermé à l'arrêt. Toutes les
requêtes passent par les trois helpers ci-dessous :
- fetchall()    : SELECT → liste de dicts ;
- execute()     : une requête d'écriture isolée (autocommit) ;
- transaction() : plusieurs écritures atomiques (tout ou rien).

`pool_recycle` renouvelle les connexions avant le `wait_timeout` du serveur :
sans lui, la première requête après une longue inactivité échoue sur une
connexion fermée côté MySQL. Charset utf8mb4 : obligatoire pour les emojis."""
from __future__ import annotations

from contextlib import asynccontextmanager

import aiomysql

from bot.core.config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from bot.core.logger import log

_POOL_RECYCLE = 3600  # secondes


class Database:
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    @classmethod
    async def connect(cls) -> "Database":
        missing = [n for n, v in (("DB_HOST", DB_HOST), ("DB_NAME", DB_NAME), ("DB_USER", DB_USER)) if not v]
        if missing:
            raise RuntimeError(f"Variable(s) manquante(s) dans le .env : {', '.join(missing)}")
        pool = await aiomysql.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=5,
            pool_recycle=_POOL_RECYCLE,
        )
        log.info(f"[DB] Connecté à {DB_NAME}@{DB_HOST}:{DB_PORT}.")
        return cls(pool)

    async def close(self) -> None:
        self._pool.close()
        await self._pool.wait_closed()

    async def fetchall(self, sql: str, args=None) -> list[dict]:
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, args)
                return list(await cur.fetchall())

    async def execute(self, sql: str, args=None) -> int:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                return await cur.execute(sql, args)

    @asynccontextmanager
    async def transaction(self):
        """Curseur dont toutes les écritures sont validées ensemble à la sortie
        du bloc, ou annulées si une exception le traverse."""
        async with self._pool.acquire() as conn:
            await conn.begin()
            cur = await conn.cursor()
            try:
                yield cur
                await conn.commit()
            except BaseException:
                await conn.rollback()
                raise
            finally:
                await cur.close()


_db: Database | None = None


def get_db() -> Database | None:
    """Base courante, ou None tant qu'aucune connexion n'est ouverte (tests :
    les stores restent alors purement en mémoire)."""
    return _db


def set_db(db: Database | None) -> None:
    global _db
    _db = db


async def init_db() -> Database:
    db = await Database.connect()
    set_db(db)
    return db


async def close_db() -> None:
    db = get_db()
    set_db(None)
    if db is not None:
        await db.close()
