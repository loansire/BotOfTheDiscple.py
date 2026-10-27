# -*- coding: utf-8 -*-
import asyncio
import time
from datetime import datetime

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

from bot.bungie.client import bungie
from bot.utils.logger import log


def _reformat_pubdate(item: dict) -> None:
    """Reformate PubDate en place : ISO → 'YYYY-MM-DD | HH:MM:SS'."""
    pubdate = item.get("PubDate", "")
    try:
        dt = datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%SZ")
        item["PubDate"] = dt.strftime("%Y-%m-%d | %H:%M:%S")
    except ValueError:
        log.warning(f"[News] Format de date invalide : {pubdate}")


# Les deux types d'alertes (TWID, patch notes) interrogent les MÊMES flux RSS à
# chaque poll : on garde chaque flux quelques secondes pour ne faire qu'un appel
# par langue et par poll (au lieu d'un par type d'alerte).
_FEED_TTL = 30  # secondes
_feed_cache: dict[str, tuple[float, dict | None]] = {}
_feed_locks: dict[str, asyncio.Lock] = {}

# Résultat de la détection de langue par article FR (UniqueIdentifier → bool) :
# langdetect est coûteux et synchrone, inutile de le relancer chaque minute.
_is_french: dict[str, bool] = {}


async def _get_feed(language: str) -> dict | None:
    lock = _feed_locks.setdefault(language, asyncio.Lock())
    async with lock:
        cached = _feed_cache.get(language)
        if cached and time.monotonic() - cached[0] < _FEED_TTL:
            return cached[1]
        payload = await bungie.get_rss_articles(language=language, page_token="0", includebody=True)
        _feed_cache[language] = (time.monotonic(), payload)
        return payload


def _detect_french(html: str) -> bool:
    try:
        return detect(html) == "fr"
    except LangDetectException:
        return False


async def _translation_available(item: dict) -> bool:
    key = item.get("UniqueIdentifier") or item.get("Link", "")
    if key not in _is_french:
        _is_french[key] = await asyncio.to_thread(_detect_french, item.get("HtmlContent", ""))
    return _is_french[key]


def _iter_articles(payload: dict | None):
    if payload and "Response" in payload and "NewsArticles" in payload["Response"]:
        yield from payload["Response"]["NewsArticles"]


async def get_latest_article(language: str, keyword: str) -> tuple[dict | None, bool]:
    """Renvoie (article, traduction_fr_disponible) pour le mot-clé donné.

    On vérifie en plus que la version FR existe ET est réellement en français
    (Bungie publie parfois le contenu EN sous l'URL FR avant traduction)."""
    if language == "fr":
        articles = french_articles = await _get_feed("fr")
    else:
        articles, french_articles = await asyncio.gather(_get_feed(language), _get_feed("fr"))

    is_translation_available = False
    for item in _iter_articles(french_articles):
        if keyword in item.get("Link", ""):
            is_translation_available = await _translation_available(item)
            break

    for item in _iter_articles(articles):
        if keyword in item.get("Link", ""):
            # Copie : le flux est partagé via le cache, ne pas le muter.
            item = dict(item)
            _reformat_pubdate(item)
            return item, is_translation_available

    return None, False