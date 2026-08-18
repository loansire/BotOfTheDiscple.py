# -*- coding: utf-8 -*-
"""Feature Table de butin (/loottable).

Données MANUELLES (Ressources/LootTable/loot_tables.json), métadonnées d'items
résolues automatiquement via la définition Bungie. Aucune cadence, aucun
message persistant : la feature répond à une commande, point."""
from .models import LootActivity, LootItem
from .service import get_loot_table, list_activities

__all__ = ["LootActivity", "LootItem", "get_loot_table", "list_activities"]
