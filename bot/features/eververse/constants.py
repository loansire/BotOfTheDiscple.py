# -*- coding: utf-8 -*-
"""Constantes Eververse (boutique de Tess Everis).

Les vendor hashes sont des identifiants publics du jeu (comme XUR_VENDORS ou
les hashes de type d'activité) : ils vivent dans le code, pas dans le .env.

Les items en rotation sont éclatés sur plusieurs sous-vendors « rotator »
(bright dust + silver). On les regroupe en 3 sections d'affichage fixes ; SECTIONS
définit l'ordre des messages ET l'ordre des vendors à l'intérieur de chaque
message. `currency` pilote l'affichage du coût :
  - "dust"   → coût affiché (Poussière brillante + quantité)
  - "silver" → coût masqué (offre en Argentum, monnaie réelle)
"""

# Hashes des monnaies de coût (confirmés par le dump).
BRIGHT_DUST_HASH = 2817410917
SILVER_HASH = 3147280338

# Emoji custom Discord de la Poussière brillante (coût affiché pour "dust").
DUST_EMOJI = "<:Dust:1526717375833964626>"

# Emoji custom Discord de Tess Everis (affiché dans le titre de chaque message).
TESS_EMOJI = "<:Tess:1527021352245268675>"

# Topic d'abonnement unique (un salon, 3 messages persistants).
TOPIC = "eververse"

# Sections d'affichage. Ordre de la liste = ordre des 3 messages. Ordre des
# `vendors` = ordre des items dans le message. Commentaires = clé interne Bungie.
SECTIONS: list[dict] = [
    {
        "id": "main",
        "title": "Tess - Poussière brillante",
        "currency": "dust",
        "vendors": [
            2168194999,  # exotic_weapon_ornaments
            2031393824,  # exotic_and_legendary_armor_ornaments
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
    {
        "id": "silver",
        "title": "Tess - Offres d'Argentum",
        "currency": "silver",
        "vendors": [
            3445703438,  # exotic_emotes
            3358239265,  # exotic_ghosts
            1400187966,  # exotic_ships
            2739911710,  # exotic_vehicles
            4228941413,  # legendary_emotes
            249262409,   # legendary_finishers
        ],
    },
]