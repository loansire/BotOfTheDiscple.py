# -*- coding: utf-8 -*-
"""Constantes Eververse (boutique de Tess Everis).

Les vendor hashes sont des identifiants publics du jeu (comme XUR_VENDORS ou
les hashes de type d'activité) : ils vivent dans le code, pas dans le .env.

Les items en rotation sont éclatés sur plusieurs sous-vendors « rotator »
(bright dust). On les regroupe en 2 sections d'affichage fixes ; SECTIONS
définit l'ordre des messages ET l'ordre des vendors à l'intérieur de chaque
message. `currency` pilote l'affichage du coût :
  - "dust"   → coût affiché (Poussière brillante + quantité)
"""

# Hashes des monnaies de coût (confirmés par le dump). SILVER_HASH conservé
# pour référence : la section Argentum a été retirée de l'affichage.
BRIGHT_DUST_HASH = 2817410917
SILVER_HASH = 3147280338

# Emoji custom Discord de la Poussière brillante (coût affiché pour "dust").
DUST_EMOJI = "<:Dust:1526717375833964626>"

# Emoji custom Discord de Tess Everis (affiché dans le titre de chaque message).
TESS_EMOJI = "<:Tess:1527021352245268675>"

# Topic d'abonnement unique (un salon, messages persistants).
TOPIC = "eververse"

# ── Vendor d'ornements d'armure (spécifique classe) ─────────────────────
# Ce vendor a un inventaire SPÉCIFIQUE À LA CLASSE du personnage qui l'interroge.
# On l'appelle donc une fois PAR personnage (Titan / Arcaniste / Chasseur) pour
# afficher les 3 versions à la suite.
#
# Il conserve sa POSITION déclarative dans SECTIONS (2e vendor de la section
# principale) : grouping.py N'en lit PAS le contenu depuis le fetch groupé
# (get_all_vendor_sales, qui ne renvoie que la version du perso principal → ça
# créerait un doublon Titan) et injecte à sa place les items multi-classes
# résolus en amont par le service.
ARMOR_ORNAMENTS_VENDOR = 2031393824

# Ordre d'affichage des classes pour ce vendor.
#   (clé de personnage, libellé affiché AU-DESSUS du coût)
# La clé est résolue en character_id côté service.py (via bot.config).
ARMOR_ORNAMENT_CLASSES = [
    ("main", "Ornement Titan"),
    ("warlock", "Ornement Arcaniste"),
    ("hunter", "Ornement Chasseur"),
]

# Sections d'affichage. Ordre de la liste = ordre des messages. Ordre des
# `vendors` = ordre des items dans le message. Commentaires = clé interne Bungie.
SECTIONS: list[dict] = [
    {
        "id": "main",
        "title": "Tess - Poussière brillante",
        "currency": "dust",
        "vendors": [
            2168194999,  # exotic_weapon_ornaments
            2031393824,  # exotic_and_legendary_armor_ornaments (multi-classe)
            3118972542,  # exotic_emotes
            3702989297,  # exotic_ghosts
            4020265966,  # exotic_ships
            1105106638,  # exotic_vehicles
        ],
    },
    {
        "id": "other",
        "title": "Tess - Poussière brillante",
        "currency": "dust",
        "vendors": [
            2184482416,  # legendary_and_rare_emotes_and_finishers
            1446296883,  # legendary_and_rare_ghost_projections
            2041776156,  # legendary_shaders
            213864513,   # legendary_spawnfx
        ],
    },
]