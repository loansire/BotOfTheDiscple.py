# -*- coding: utf-8 -*-
import json
import random
from collections import Counter

from bot.config import RESOURCES_DIR

RAID_JSON = RESOURCES_DIR / "RaidRandomizer" / "raid_data.json"
DUNGEON_JSON = RESOURCES_DIR / "DungeonRandomizer" / "dungeon_data.json"


def load_data(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def weighted_pick(choices: list[str | None], data: dict) -> tuple[str, Counter]:
    """Tire un item au sort, pondéré par sa fréquence dans `choices`.

    Si aucun choix fourni, tire parmi toutes les clés de `data`.
    Retourne (item_choisi, comptage_des_choix).
    """
    selected = [c for c in choices if c]
    if not selected:
        selected = list(data.keys())

    counts = Counter(selected)
    weighted = [item for item, n in counts.items() for _ in range(n)]
    return random.choice(weighted), counts