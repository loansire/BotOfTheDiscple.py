# -*- coding: utf-8 -*-
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


def _iter_articles(payload: dict | None):
    if payload and "Response" in payload and "NewsArticles" in payload["Response"]:
        yield from payload["Response"]["NewsArticles"]


async def get_latest_article(language: str, keyword: str) -> tuple[dict | None, bool]:
    """Renvoie (article, traduction_fr_disponible) pour le mot-clé donné.

    On vérifie en plus que la version FR existe ET est réellement en français
    (Bungie publie parfois le contenu EN sous l'URL FR avant traduction)."""
    articles = await bungie.get_rss_articles(language=language, page_token="0", includebody=True)
    french_articles = await bungie.get_rss_articles(language="fr", page_token="0", includebody=True)

    is_translation_available = False
    for item in _iter_articles(french_articles):
        if keyword in item.get("Link", ""):
            try:
                if detect(item.get("HtmlContent", "")) == "fr":
                    is_translation_available = True
            except LangDetectException:
                pass
            break

    for item in _iter_articles(articles):
        if keyword in item.get("Link", ""):
            _reformat_pubdate(item)
            return item, is_translation_available

    return None, False