# -*- coding: utf-8 -*-
"""Import UNIQUE des anciens fichiers JSON vers la base.

Lancé automatiquement par open_storage() au démarrage : si la clé
`legacy_import.done` est absente de compute_state, chaque ancien fichier
présent sur disque est lu et recopié en base, puis la clé est posée. Les
démarrages suivants n'importent plus rien. Les fichiers ne sont ni modifiés ni
supprimés (retour arrière possible) : une fois la migration vérifiée, ils
peuvent être effacés à la main.

Fichiers repris :
- Ressources/AlertDatabase/*.json : abonnements, messages publiés, état de la
  pipeline, signatures, défis Avant-garde, anti-doublons news / maintenance ;
- Ressources/Manifest/bungie_tokens.json : tokens OAuth ;
- données éditées à la main : loot_tables.json, wishes.json,
  lost_sector_extra.json, permanent_activities.json, vendor_whitelist.json.

Le cache du manifest Bungie (Ressources/Manifest/Destiny*.json, etc.) n'est
PAS importé : c'est une copie régénérable du manifest, propre au calcul."""
from __future__ import annotations

from pathlib import Path

from bot.core.config import ALERTS_DIR, BOT_ID, MANIFEST_DIR, RESOURCES_DIR
from bot.core.jsonio import load_json
from bot.core.logger import log
from bot.db.database import get_db
from bot.storage.base import flush
from bot.storage.compute_state import compute_state
from bot.storage.messages import CONTENT, Entry, messages
from bot.storage.subscriptions import subscriptions

DONE_KEY = "legacy_import.done"

LOOT_TABLES = RESOURCES_DIR / "LootTable" / "loot_tables.json"
WISHES = RESOURCES_DIR / "RivenWishes" / "wishes.json"
LOST_SECTOR_EXTRA = RESOURCES_DIR / "Weekly" / "lost_sector_extra.json"
PERMANENT = RESOURCES_DIR / "Weekly" / "permanent_activities.json"
VENDOR_WHITELIST = MANIFEST_DIR / "vendor_whitelist.json"
TOKENS = MANIFEST_DIR / "bungie_tokens.json"

# Fichiers d'état « multi-message » : {"guilds": {gid: {message_ids, hash}}}
_MULTI_FILES = {"ada": "ada_messages.json", "eververse": "eververse_messages.json"}
# Fichiers d'état « mono-message » : {gid: {message_id, hash}}
_SINGLE_FILES = {"ascendant": "ascendant_state.json", "distortion": "distortion_state.json"}


def _read(path: Path, expected=dict):
    data = load_json(path)
    return data if isinstance(data, expected) else None


def _put(guild_id, topic: str, slots: dict, content_hash) -> None:
    slots = {slot: [str(i) for i in ids if i] for slot, ids in slots.items()}
    messages.put(guild_id, topic, Entry(slots={s: ids for s, ids in slots.items() if ids}, hash=content_hash))


# ── Anciens états (AlertDatabase) ───────────────────────────────────────


def _import_states() -> list[str]:
    done = []
    data = _read(ALERTS_DIR / "subscriptions.json")
    if data is not None:
        subscriptions.replace_all(data)
        done.append("subscriptions.json")

    for topic, name in _MULTI_FILES.items():
        data = _read(ALERTS_DIR / name)
        if data is None:
            continue
        for gid, entry in data.get("guilds", {}).items():
            _put(gid, topic, {CONTENT: entry.get("message_ids", [])}, entry.get("hash", ""))
        done.append(name)

    for topic, name in _SINGLE_FILES.items():
        data = _read(ALERTS_DIR / name)
        if data is None:
            continue
        for gid, entry in data.items():
            _put(gid, topic, {CONTENT: [entry.get("message_id")]}, entry.get("hash"))
        done.append(name)

    data = _read(ALERTS_DIR / "weekly_messages.json")
    if data is not None:
        for gid, topics in data.get("guilds", {}).items():
            for topic, entry in topics.items():
                ids = list(entry.get("message_ids", []))
                if entry.get("message_id"):
                    ids.append(entry["message_id"])
                _put(gid, topic, {CONTENT: ids}, entry.get("hash"))
        for topic, sig in data.get("signatures", {}).items():
            compute_state.set(f"weekly.signature.{topic}", sig)
        if data.get("vanguard_challenges"):
            compute_state.set("weekly.vanguard_challenges", data["vanguard_challenges"])
        done.append("weekly_messages.json")

    data = _read(ALERTS_DIR / "xur_messages.json")
    if data is not None:
        for gid, entry in data.get("guilds", {}).items():
            if "message_ids" in entry and "status_id" not in entry:
                old = list(entry["message_ids"])  # ancien format : 1er = statut
                status, cats = old[:1], old[1:]
            else:
                status, cats = [entry.get("status_id")], entry.get("category_ids", [])
            _put(gid, "xur", {"status": status, CONTENT: cats}, entry.get("hash", ""))
        done.append("xur_messages.json")

    data = _read(ALERTS_DIR / "pipeline_state.json")
    if data is not None:
        if data.get("last_reset"):
            compute_state.set("pipeline.last_reset", data["last_reset"])
        if data.get("pending_weekdays"):
            compute_state.set("pipeline.pending_weekdays", data["pending_weekdays"])
        done.append("pipeline_state.json")

    data = _read(ALERTS_DIR / "news_state.json")
    if data is not None:
        for keyword, article_id in data.items():
            compute_state.set(f"news.last_id.{keyword}", article_id)
        done.append("news_state.json")

    data = _read(ALERTS_DIR / "state.json")
    if data is not None:
        for game, state in data.items():
            compute_state.set(f"maintenance.{game}", state)
        done.append("state.json")

    data = _read(TOKENS)
    if data:
        compute_state.set("bungie.oauth", data)
        done.append("bungie_tokens.json")
    return done


# ── Données éditées à la main ───────────────────────────────────────────


async def _import_static(db) -> list[str]:
    done = []
    async with db.transaction() as cur:
        data = _read(LOOT_TABLES)
        if data is not None:
            tables = [(k, v) for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)]
            await cur.executemany(
                "REPLACE INTO compute_loot_table (activity_key, label, banner_file, type, sort_order)"
                " VALUES (%s, %s, %s, %s, %s)",
                [(k, v.get("label") or k, v.get("banner"), v.get("type"), i) for i, (k, v) in enumerate(tables)],
            )
            items = [(k, pos, int(h)) for k, v in tables for pos, h in enumerate(v.get("items", []))]
            if items:
                await cur.executemany(
                    "REPLACE INTO compute_loot_table_item (activity_key, position, item_hash)"
                    " VALUES (%s, %s, %s)",
                    items,
                )
            done.append("loot_tables.json")

        data = _read(WISHES)
        if data is not None and data.get("voeux"):
            await cur.executemany(
                "REPLACE INTO compute_wish (position, name, description, image_file, button_label)"
                " VALUES (%s, %s, %s, %s, %s)",
                [
                    (i, w.get("nom", ""), w.get("description", ""), w.get("image"), w.get("BoutonName"))
                    for i, w in enumerate(data["voeux"])
                ],
            )
            done.append("wishes.json")

        data = _read(LOST_SECTOR_EXTRA)
        if data is not None:
            rows = [
                (int(h), kind, name, int(count), pos)
                for h, entry in data.items()
                for kind in ("shields", "champions")
                for pos, (name, count) in enumerate((entry.get(kind) or {}).items())
            ]
            if rows:
                await cur.executemany(
                    "REPLACE INTO compute_lost_sector_extra (activity_hash, kind, name, count, position)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    rows,
                )
            done.append("lost_sector_extra.json")

        data = _read(PERMANENT, list)
        if data:
            await cur.executemany(
                "REPLACE INTO compute_permanent_activity (activity_hash) VALUES (%s)",
                [(int(h),) for h in data],
            )
            done.append("permanent_activities.json")

        data = _read(VENDOR_WHITELIST)
        if data is not None:
            await cur.executemany(
                "REPLACE INTO compute_vendor_whitelist (category, positions) VALUES (%s, %s)",
                [(cat, ",".join(str(p) for p in positions)) for cat, positions in data.items()],
            )
            done.append("vendor_whitelist.json")
    return done


async def import_legacy_json() -> None:
    db = get_db()
    if db is None or compute_state.get(DONE_KEY):
        return
    done = _import_states() + await _import_static(db)
    compute_state.set(DONE_KEY, {"bot_id": BOT_ID, "files": done})
    await flush()
    # Les données statiques viennent d'être écrites : rechargement du cache.
    from bot.storage.static_data import static_data

    await static_data.load(db)
    if done:
        log.info(f"[DB] Import des anciens fichiers JSON : {', '.join(done)}.")
    else:
        log.info("[DB] Aucun ancien fichier JSON à importer.")
