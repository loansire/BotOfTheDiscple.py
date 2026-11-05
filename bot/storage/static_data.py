# -*- coding: utf-8 -*-
"""Données éditées à la main dans la base (phpMyAdmin), tables compute_* :

- compute_loot_table / compute_loot_table_item → loot_tables()
- compute_wish                                 → wishes()
- compute_lost_sector_extra                    → lost_sector_extra()
- compute_permanent_activity                   → permanent_activities()
- compute_vendor_whitelist                     → vendor_whitelist()

Le bot ne fait que les LIRE : chargées au démarrage puis relues toutes les
RELOAD_EVERY secondes (cf. bot/storage/__init__.py), une modification prend
donc effet sans redémarrage. Les getters renvoient les mêmes formes que les
anciens fichiers JSON ; les valeurs sont PARTAGÉES avec le cache (ne pas les
modifier)."""
from __future__ import annotations

from bot.core.logger import log
from bot.db.database import Database
from bot.storage.base import Table

RELOAD_EVERY = 600  # secondes


def parse_positions(raw: str) -> list[int]:
    """'2, 3,4' → [2, 3, 4] (morceaux non numériques ignorés)."""
    return [int(p) for p in (raw or "").replace(";", ",").split(",") if p.strip().isdigit()]


class StaticData(Table):
    def __init__(self):
        super().__init__()
        self.loot_tables: dict[str, dict] = {}
        self.wishes: list[dict] = []
        self.lost_sector_extra: dict[str, dict] = {}
        self.permanent_activities: set[int] = set()
        self.vendor_whitelist: dict[str, list[int]] = {}

    async def _load(self, db: Database) -> None:
        tables: dict[str, dict] = {}
        for row in await db.fetchall(
            "SELECT activity_key, label, banner_file, type FROM compute_loot_table"
            " ORDER BY sort_order, activity_key"
        ):
            tables[row["activity_key"]] = {
                "label": row["label"], "banner": row["banner_file"], "type": row["type"], "items": [],
            }
        for row in await db.fetchall(
            "SELECT activity_key, item_hash FROM compute_loot_table_item ORDER BY activity_key, position"
        ):
            if row["activity_key"] in tables:
                tables[row["activity_key"]]["items"].append(int(row["item_hash"]))

        wishes = [
            {
                "nom": row["name"],
                "description": row["description"],
                "image": row["image_file"] or "",
                "BoutonName": row["button_label"],
            }
            for row in await db.fetchall(
                "SELECT name, description, image_file, button_label FROM compute_wish ORDER BY position"
            )
        ]

        extra: dict[str, dict] = {}
        for row in await db.fetchall(
            "SELECT activity_hash, kind, name, count FROM compute_lost_sector_extra"
            " ORDER BY activity_hash, kind, position"
        ):
            entry = extra.setdefault(str(row["activity_hash"]), {})
            entry.setdefault(row["kind"], {})[row["name"]] = int(row["count"])

        permanent = {
            int(row["activity_hash"])
            for row in await db.fetchall("SELECT activity_hash FROM compute_permanent_activity")
        }

        whitelist = {
            row["category"]: parse_positions(row["positions"])
            for row in await db.fetchall("SELECT category, positions FROM compute_vendor_whitelist")
        }

        self.loot_tables, self.wishes, self.lost_sector_extra = tables, wishes, extra
        self.permanent_activities, self.vendor_whitelist = permanent, whitelist

    async def _write(self, db: Database, keys: set) -> None:
        """Lecture seule : rien à écrire (l'import initial écrit lui-même)."""

    async def reload(self, db: Database) -> None:
        try:
            await self.load(db)
        except Exception as e:
            log.warning(f"[DB] Relecture des données éditées à la main échouée : {e}")


static_data = StaticData()


def loot_tables() -> dict[str, dict]:
    """{ key: {label, banner, type, items: [itemHash...]} }, dans l'ordre."""
    return static_data.loot_tables


def wishes() -> list[dict]:
    """[{nom, description, image, BoutonName}], dans l'ordre du menu."""
    return static_data.wishes


def lost_sector_extra() -> dict[str, dict]:
    """{ "<activity_hash>": {"shields": {nom: n}, "champions": {nom: n}} }."""
    return static_data.lost_sector_extra


def permanent_activities() -> set[int]:
    return static_data.permanent_activities


def vendor_whitelist() -> dict[str, list[int]]:
    """{ catégorie: [positions 1-based] } ; catégorie absente = tout garder."""
    return static_data.vendor_whitelist
