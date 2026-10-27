# -*- coding: utf-8 -*-
"""Petits utilitaires asyncio partagés."""
from __future__ import annotations

import asyncio
from typing import Awaitable, Iterable, TypeVar

T = TypeVar("T")


async def gather_limited(aws: Iterable[Awaitable[T]], limit: int = 5) -> list[T]:
    """asyncio.gather avec au plus `limit` tâches simultanées, résultats dans
    l'ordre d'entrée. Sert à résoudre des items en parallèle sans déclencher le
    throttling de l'API Bungie. Une exception est propagée comme avec gather."""
    sem = asyncio.Semaphore(limit)

    async def run(aw: Awaitable[T]) -> T:
        async with sem:
            return await aw

    return await asyncio.gather(*(run(aw) for aw in aws))
