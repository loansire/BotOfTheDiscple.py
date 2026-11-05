# -*- coding: utf-8 -*-
"""Persistance SQL : abonnements, messages publiés, état du calcul et données
éditées à la main.

Cycle de vie (cf. Main.py) :
    await open_storage()   connexion, migrations, import des anciens JSON,
                           chargement des caches, relecture périodique
    ...                    le bot tourne (les stores lisent en mémoire)
    await close_storage()  dernière écriture en attente, fermeture"""
from __future__ import annotations

import asyncio

from bot.core.logger import log
from bot.db.database import close_db, get_db, init_db
from bot.db.migrate import migrate
from bot.storage import base
from bot.storage.static_data import RELOAD_EVERY

# Import des stores : chacun s'enregistre dans base._TABLES à l'import.
from bot.storage import compute_state, messages, static_data, subscriptions  # noqa: F401

_reload_task: asyncio.Task | None = None


async def _reload_static_loop() -> None:
    while True:
        await asyncio.sleep(RELOAD_EVERY)
        db = get_db()
        if db is not None:
            await static_data.static_data.reload(db)


async def open_storage() -> None:
    global _reload_task
    from bot.storage.legacy_import import import_legacy_json

    db = await init_db()
    await migrate(db)
    await base.load_all()
    await import_legacy_json()
    if _reload_task is None:
        _reload_task = asyncio.create_task(_reload_static_loop())


async def close_storage() -> None:
    global _reload_task
    if _reload_task is not None:
        _reload_task.cancel()
        _reload_task = None
    try:
        await base.flush()
    except Exception as e:
        log.error(f"[DB] Écriture finale échouée : {e}")
    await close_db()
