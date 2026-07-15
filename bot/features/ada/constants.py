# -*- coding: utf-8 -*-
"""Constantes Ada-1 (marchande de mods de la Tour).

Le vendor hash est un identifiant public du jeu (comme XUR_VENDORS ou les
hashes de type d'activité) : il vit dans le code, pas dans le .env.

Ada-1 est un vendor PERMANENT (toujours présente à la Tour) : pas de fenêtre
présent/absent. Son inventaire tourne une fois par semaine, au reset du MARDI.

Module volontairement SANS import (aucun `bot.config`) : la logique de filtrage
(filtering.py) peut ainsi être testée sans .env.
"""

# Hash public du vendor Ada-1.
ADA_VENDOR_HASH = 350061650

# Topic d'abonnement (un salon ; 1 message persistant, re-découpé seulement si
# le plafond CV2 est dépassé — cf. rendu au Lot 2).
TOPIC = "ada"

# Libellé affiché dans le message.
ADA_LABEL = "Ada-1"

# Emoji de titre du message (emoji custom Ada-1).
ADA_EMOJI = "<:Ada:1527021353591374024>"

# Emoji custom Discord du Glimmer (coût affiché sur chaque item).
GLIMMER_EMOJI = "<:Glimer:1526889023963136030>"

# ── Filtre positionnel ─────────────────────────────────────────────────
# Règle STRUCTURELLE (pas « par item ») maintenue en code : on IGNORE les N
# premières cases et les M dernières cases de sales.data, triées par index
# croissant (= ordre des « cases » dans l'interface du PNJ).
# Demande actuelle : retirer les positions 1/2/3 (3 premières) et la dernière.
ADA_SKIP_LEADING = 3
ADA_SKIP_TRAILING = 1