# -*- coding: utf-8 -*-
"""Constantes Xûr.

Les vendor hashes sont des identifiants publics du jeu (comme les hashes de
type d'activité dans weekly/filters.py), pas des secrets : ils vivent dans le
code, pas dans le .env.

Ordre de la liste = ordre d'affichage des catégories dans la vue.

Plusieurs catégories peuvent partager le MÊME vendor_hash : le vendor « Armes »
(3751514131) expose à la fois les armes exotiques, les armes légendaires et les
armures légendaires. On le déclare donc en trois clés distinctes pointant vers
le même hash, chacune filtrée par sa propre plage de positions (cf.
vendor_whitelist.json). Le fetch réseau est mutualisé par hash dans service.py
(get_vendor_sales n'a pas de cache).
"""
from bot.bungie.reset import FRIDAY, TUESDAY  # noqa: F401  (ré-export — dédup avec reset.py)
from bot.config import MANIFEST_DIR

# clé interne → (vendor_hash, libellé affiché, emoji custom de catégorie)
XUR_VENDORS: dict[str, tuple[int, str, str]] = {
    "armor": (2190858386, "ARMURES", "<:Engramme_Exo:1270719580322660425>"),
    "exotics-weapons": (3751514131, "ARMES EXOTIQUES", "<:Xur:1527021351368659205>"),
    "legendaries-weapons": (3751514131, "ARMES LÉGENDAIRES", "<:Xur:1527021351368659205>"),
    "legendaries-armors": (3751514131, "ARMURES LÉGENDAIRES", "<:Xur:1527021351368659205>"),
    "materials": (537912098, "OFFRE MATÉRIAUX", "<:Matrice:1270042340324544604>"),
}

# Composant Vendors à demander (sales = items en vente).
VENDOR_COMPONENTS = "402"

# Jours de la semaine : importés de reset.py (source unique de vérité).
# FRIDAY = 4, TUESDAY = 1 — ré-exportés ci-dessus pour les imports existants.

# Whitelist de POSITIONS par catégorie (maintenue à la main, hors code).
# Clés = clés internes de XUR_VENDORS ; valeurs = liste de positions 1-based
# des « cases » à conserver (1 = 1ère case du PNJ, dans l'ordre des clés
# sales.data triées). On filtre par RANG, pas par clé : la case n°6 reste la
# n°6 même si sa clé Bungie change d'une semaine à l'autre.
#
# Plusieurs catégories partageant un même vendor_hash (le vendor Armes) sont
# chacune découpées dans le MÊME bloc sales via des plages de positions
# disjointes (ex. exotics-weapons = [2..7], legendaries-weapons = [8..16],
# legendaries-armors = [19..23]). Conventions :
#   - catégorie absente / fichier inexistant → on garde TOUT le vendor
#   - catégorie présente avec liste de positions → on ne garde que ces cases
#   - catégorie présente avec liste vide []      → on n'affiche rien
VENDOR_WHITELIST_PATH = MANIFEST_DIR / "vendor_whitelist.json"