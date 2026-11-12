# -*- coding: utf-8 -*-
"""Connexions MySQL / MariaDB (pools aiomysql).

Deux bases, chacune avec son pool, ouvertes au démarrage (cf. bot/storage) et
fermées à l'arrêt :
- la base d'ÉTAT (DB_*)         : abonnements, messages publiés, état du
  calcul. Propre à chaque bot, jamais partagée ;
- la base de CONTENU (CONTENT_DB_*) : publications prêtes à afficher
  (content_*), écrites par le live et lues par chaque bot qui publie.
  Optionnelle : sans CONTENT_DB_HOST, le contenu vit dans la base d'état.

Toutes les requêtes passent par les trois helpers de Database :
- fetchall()    : SELECT → liste de dicts ;
- execute()     : une requête d'écriture isolée (autocommit) ;
- transaction() : plusieurs écritures atomiques (tout ou rien).

`pool_recycle` renouvelle les connexions avant le `wait_timeout` du serveur :
sans lui, la première requête après une longue inactivité échoue sur une
connexion fermée côté MySQL. Charset utf8mb4 : obligatoire pour les emojis."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

import aiomysql

from bot.core import config
from bot.core.logger import log

_POOL_RECYCLE = 3600  # secondes


@dataclass(frozen=True)
class DbConfig:
    label: str  # préfixe des variables du .env (messages d'erreur, logs)
    host: str | None
    port: int
    name: str | None
    user: str | None
    password: str


def state_config() -> DbConfig:
    return DbConfig("DB", config.DB_HOST, config.DB_PORT, config.DB_NAME, config.DB_USER,
                    config.DB_PASSWORD)


def content_config() -> DbConfig | None:
    """None : pas de base de contenu dédiée (le contenu vit dans la base d'état)."""
    if not config.CONTENT_DB_HOST:
        return None
    return DbConfig("CONTENT_DB", config.CONTENT_DB_HOST, config.CONTENT_DB_PORT,
                    config.CONTENT_DB_NAME, config.CONTENT_DB_USER, config.CONTENT_DB_PASSWORD)


class Database:
    def __init__(self, pool: aiomysql.Pool):
        self._pool = pool

    @classmethod
    async def connect(cls, cfg: DbConfig) -> "Database":
        missing = [f"{cfg.label}_{n}" for n, v in (("HOST", cfg.host), ("NAME", cfg.name), ("USER", cfg.user)) if not v]
        if missing:
            raise RuntimeError(f"Variable(s) manquante(s) dans le .env : {', '.join(missing)}")
        pool = await aiomysql.create_pool(
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            db=cfg.name,
            charset="utf8mb4",
            autocommit=True,
            minsize=1,
            maxsize=5,
            pool_recycle=_POOL_RECYCLE,
        )
        log.info(f"[DB] {cfg.label} : connecté à {cfg.name}@{cfg.host}:{cfg.port}.")
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
_content_db: Database | None = None


def get_db() -> Database | None:
    """Base d'état, ou None tant qu'aucune connexion n'est ouverte (tests :
    les stores restent alors purement en mémoire)."""
    return _db


def set_db(db: Database | None) -> None:
    global _db
    _db = db


def get_content_db() -> Database | None:
    """Base de contenu ; à défaut de base dédiée, la base d'état."""
    return _content_db if _content_db is not None else _db


def set_content_db(db: Database | None) -> None:
    global _content_db
    _content_db = db


def has_content_db() -> bool:
    """True si le contenu vit dans une base dédiée (pool séparé)."""
    return _content_db is not None


async def init_db() -> Database:
    db = await Database.connect(state_config())
    set_db(db)
    return db


async def init_content_db() -> Database:
    """Ouvre la base de contenu dédiée si elle est configurée ; renvoie la
    base qui porte le contenu (dédiée, ou celle d'état)."""
    cfg = content_config()
    if cfg is not None:
        set_content_db(await Database.connect(cfg))
    else:
        log.info("[DB] Pas de CONTENT_DB_HOST : le contenu reste dans la base d'état.")
    db = get_content_db()
    if db is None:
        raise RuntimeError("Base d'état non connectée.")
    return db


async def close_db() -> None:
    content, state = _content_db, _db
    set_content_db(None)
    set_db(None)
    for db in (content, state):
        if db is not None:
            await db.close()
