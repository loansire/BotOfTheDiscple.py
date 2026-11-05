# -*- coding: utf-8 -*-
"""Stockage des publications prêtes à afficher (tables content_*).

Côté calcul :
- save_post(post) : écrit une NOUVELLE version si le contenu a changé
  (comparaison du hash avec la dernière version), sinon ne fait rien. Tout
  est écrit dans une seule transaction : une version n'est jamais visible à
  moitié écrite.
- prune()         : supprime les versions de plus de KEEP_DAYS (sauf la
  dernière de chaque topic) et les images plus référencées.

Côté publication :
- latest_headers() : dernière version de chaque topic (une seule requête,
  appelée par la boucle de publication) ;
- load_post()      : messages et composants d'une version (mis en cache :
  une version ne change jamais) ;
- load_images()    : octets des images (mis en cache par id).

Les versions sont immuables : un contenu modifié = une nouvelle version."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone

from bot.content.model import Component, Message, Post
from bot.db.database import Database, get_db

KEEP_DAYS = 7
_POST_CACHE_SIZE = 64
_IMAGE_CACHE_SIZE = 512

_COMPONENT_COLUMNS = [f.name for f in fields(Component) if f.name not in ("image_data", "image_mime")]
_BOOL_COLUMNS = {"inline_field", "btn_disabled"}


@dataclass(frozen=True)
class PostHeader:
    topic: str
    version: int
    mode: str
    content_hash: str
    period_start: datetime | None
    expires_at: datetime | None
    computed_at: datetime | None


def _db() -> Database:
    db = get_db()
    if db is None:
        raise RuntimeError("Base non connectée.")
    return db


def _header(row: dict) -> PostHeader:
    return PostHeader(**{f.name: row.get(f.name) for f in fields(PostHeader)})


def _utc_naive(value: datetime | None) -> datetime | None:
    """Les colonnes DATETIME n'ont pas de fuseau : on y range de l'UTC."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


# ── Écriture (calcul) ───────────────────────────────────────────────────


async def latest_header(topic: str) -> PostHeader | None:
    rows = await _db().fetchall(
        "SELECT topic, version, mode, content_hash, period_start, expires_at, computed_at"
        " FROM content_post WHERE topic = %s AND status = 'ready'"
        " ORDER BY version DESC LIMIT 1",
        (topic,),
    )
    return _header(rows[0]) if rows else None


async def save_post(post: Post) -> tuple[int, bool]:
    """(version, nouvelle_version_écrite). Renseigne `post.version`."""
    db = _db()
    content_hash = post.content_hash()
    latest = await latest_header(post.topic)
    if latest is not None and latest.content_hash == content_hash:
        post.version = latest.version
        post.stored_hash = content_hash
        return latest.version, False

    rows = await db.fetchall(
        "SELECT COALESCE(MAX(version), 0) AS v FROM content_post WHERE topic = %s", (post.topic,)
    )
    version = int(rows[0]["v"]) + 1

    async with db.transaction() as cur:
        # Une image à la fois : une requête multi-lignes pourrait dépasser
        # max_allowed_packet du serveur.
        for image_id, (data, mime) in post.images().items():
            await cur.execute(
                "INSERT INTO content_image (image_id, mime, data) VALUES (%s, %s, %s)"
                " ON DUPLICATE KEY UPDATE image_id = image_id",
                (image_id, mime, data),
            )
        await cur.execute(
            "INSERT INTO content_post (topic, version, mode, content_hash, period_start, expires_at)"
            " VALUES (%s, %s, %s, %s, %s, %s)",
            (post.topic, version, post.mode, content_hash,
             _utc_naive(post.period_start), _utc_naive(post.expires_at)),
        )
        message_rows, component_rows = [], []
        for variant, messages in post.variants.items():
            for mpos, message in enumerate(messages):
                message_rows.append((post.topic, version, variant, mpos, message.layout, message.accent_color))
                for cpos, component in enumerate(message.components):
                    row = component.row()
                    component_rows.append(
                        (post.topic, version, variant, mpos, cpos, *(row[c] for c in _COMPONENT_COLUMNS))
                    )
        if message_rows:
            await cur.executemany(
                "INSERT INTO content_message (topic, version, variant, position, layout, accent_color)"
                " VALUES (%s, %s, %s, %s, %s, %s)",
                message_rows,
            )
        if component_rows:
            columns = ", ".join(_COMPONENT_COLUMNS)
            placeholders = ", ".join(["%s"] * (5 + len(_COMPONENT_COLUMNS)))
            await cur.executemany(
                f"INSERT INTO content_component (topic, version, variant, message_pos, position, {columns})"
                f" VALUES ({placeholders})",
                component_rows,
            )
    post.version = version
    post.stored_hash = content_hash
    return version, True


async def prune(now: datetime | None = None) -> None:
    """Supprime les vieilles versions (la dernière de chaque topic est
    toujours gardée) puis les images que plus aucun composant n'utilise."""
    db = _db()
    cutoff = (now or datetime.now(timezone.utc)).replace(tzinfo=None) - timedelta(days=KEEP_DAYS)
    old = await db.fetchall(
        "SELECT p.topic, p.version FROM content_post p"
        " JOIN (SELECT topic, MAX(version) AS v FROM content_post GROUP BY topic) m"
        " ON m.topic = p.topic"
        " WHERE p.version < m.v AND p.computed_at < %s",
        (cutoff,),
    )
    if old:
        async with db.transaction() as cur:
            for row in old:
                key = (row["topic"], row["version"])
                for table in ("content_component", "content_message", "content_post"):
                    await cur.execute(f"DELETE FROM {table} WHERE topic = %s AND version = %s", key)
    await db.execute(
        "DELETE i FROM content_image i"
        " LEFT JOIN content_component c ON c.image_id = i.image_id"
        " WHERE c.image_id IS NULL AND i.created_at < %s",
        (cutoff,),
    )


# ── Lecture (publication) ───────────────────────────────────────────────

_post_cache: OrderedDict[tuple[str, int], Post] = OrderedDict()
_image_cache: OrderedDict[str, bytes] = OrderedDict()


def _remember(cache: OrderedDict, key, value, size: int) -> None:
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > size:
        cache.popitem(last=False)


async def latest_headers() -> dict[str, PostHeader]:
    """Dernière version prête de chaque topic."""
    rows = await _db().fetchall(
        "SELECT p.topic, p.version, p.mode, p.content_hash, p.period_start, p.expires_at, p.computed_at"
        " FROM content_post p"
        " JOIN (SELECT topic, MAX(version) AS v FROM content_post WHERE status = 'ready' GROUP BY topic) m"
        " ON m.topic = p.topic AND m.v = p.version"
    )
    return {row["topic"]: _header(row) for row in rows}


async def load_post(topic: str, version: int | None = None) -> Post | None:
    """Une version (la dernière si `version` est None), toutes variantes."""
    if version is None:
        header = await latest_header(topic)
        if header is None:
            return None
        version = header.version
    cached = _post_cache.get((topic, version))
    if cached is not None:
        return cached

    db = _db()
    rows = await db.fetchall(
        "SELECT mode, content_hash, period_start, expires_at FROM content_post"
        " WHERE topic = %s AND version = %s",
        (topic, version),
    )
    if not rows:
        return None
    post = Post(topic=topic, mode=rows[0]["mode"], period_start=rows[0]["period_start"],
                expires_at=rows[0]["expires_at"], version=version, stored_hash=rows[0]["content_hash"])
    for row in await db.fetchall(
        "SELECT variant, layout, accent_color FROM content_message"
        " WHERE topic = %s AND version = %s ORDER BY variant, position",
        (topic, version),
    ):
        post.variants.setdefault(row["variant"], []).append(
            Message(layout=row["layout"], accent_color=row["accent_color"])
        )
    for row in await db.fetchall(
        f"SELECT variant, message_pos, {', '.join(_COMPONENT_COLUMNS)} FROM content_component"
        " WHERE topic = %s AND version = %s ORDER BY variant, message_pos, position",
        (topic, version),
    ):
        values = {c: row[c] for c in _COMPONENT_COLUMNS}
        for c in _BOOL_COLUMNS:
            if values[c] is not None:
                values[c] = bool(values[c])
        post.variants[row["variant"]][row["message_pos"]].components.append(Component(**values))

    _remember(_post_cache, (topic, version), post, _POST_CACHE_SIZE)
    return post


async def load_images(image_ids) -> dict[str, bytes]:
    """id → octets, pour les images demandées (cache mémoire par id)."""
    wanted = {i for i in image_ids if i}
    found = {i: _image_cache[i] for i in wanted if i in _image_cache}
    missing = sorted(wanted - set(found))
    if missing:
        placeholders = ", ".join(["%s"] * len(missing))
        for row in await _db().fetchall(
            f"SELECT image_id, data FROM content_image WHERE image_id IN ({placeholders})", missing
        ):
            data = bytes(row["data"])
            found[row["image_id"]] = data
            _remember(_image_cache, row["image_id"], data, _IMAGE_CACHE_SIZE)
    return found
