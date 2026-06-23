# -*- coding: utf-8 -*-
"""Constantes Xûr.

Les vendor hashes sont des identifiants publics du jeu (comme les hashes de
type d'activité dans weekly/filters.py), pas des secrets : ils vivent dans le
code, pas dans le .env.

Ordre de la liste = ordre d'affichage des catégories dans la vue.
"""
from bot.bungie.reset import FRIDAY, TUESDAY  # noqa: F401  (ré-export — dédup avec reset.py)
from bot.config import MANIFEST_DIR

# clé interne → (vendor_hash, libellé affiché, emoji custom de catégorie)
XUR_VENDORS: dict[str, tuple[int, str, str]] = {
    "armor": (2190858386, "Armures<:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258>", "<:Casque:1352430820802957403>"),
    "weapons": (3751514131, "Armes<:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258>", "<:Pistoletmitrailleur:1305317813094711416>"),
    "materials": (537912098, "Matériaux<:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258><:Blank:1516201087944757258>", "<:Matrice:1270042340324544604>"),
}

# Composant Vendors à demander (sales = items en vente).
VENDOR_COMPONENTS = "402"

# Jours de la semaine : importés de reset.py (source unique de vérité).
# FRIDAY = 4, TUESDAY = 1 — ré-exportés ci-dessus pour les imports existants.

# Whitelist de POSITIONS par vendor (maintenue à la main, hors code).
# Clés = clés internes de XUR_VENDORS ; valeurs = liste de positions 1-based
# des « cases » à conserver (1 = 1ère case du PNJ, dans l'ordre des clés
# sales.data triées). On filtre par RANG, pas par clé : la case n°6 reste la
# n°6 même si sa clé Bungie change d'une semaine à l'autre. Conventions :
#   - vendor absent / fichier inexistant → on garde TOUT le vendor
#   - vendor présent avec liste de positions → on ne garde que ces cases
#   - vendor présent avec liste vide []      → on n'affiche rien pour ce vendor
VENDOR_WHITELIST_PATH = MANIFEST_DIR / "vendor_whitelist.json"