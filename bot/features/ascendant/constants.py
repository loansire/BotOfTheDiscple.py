# -*- coding: utf-8 -*-
"""Constantes de la feature Défis ascendants (co-localisées).

Cycle FIXE de 6 défis, un par semaine, calé sur une unique ancre (cf.
__init__.py). Chaque défi est verrouillé sur une phase de malédiction, d'où la
position de Petra. Le mapping contrat→défi permet, si l'on lit le contrat hebdo
de Petra (composant 402 VendorSales), de valider ou forcer la résolution.

Principe de centralisation minimale : ces constantes sont SPÉCIFIQUES à cette
feature (rien n'est partagé avec d'autres scripts)."""

# Emoji d'en-tête de la publication (topic « ascendant »).
ASCENDANT_EMOJI = "<:Challenge_Ascendant:1534163534970093618>"

# Ordre FIXE du cycle (index 0 = défi actif à l'ANCRE = agonarch_abyss).
DEFIS_ORDRE: tuple[str, ...] = (
    "agonarch_abyss",
    "cimmerian_garrison",
    "ouroborea",
    "forfeit_shrine",
    "shattered_ruins",
    "keep_of_honed_edges",
)

# Métadonnées par défi (libellés FR issus du manifest).
# malediction ∈ {faible, croissante, forte} → position de Petra dérivée.
DEFIS_META: dict[str, dict] = {
    "agonarch_abyss":      {"nom": "Abysse des Argonarques",       "secteur": "Baie des Souhaits Noyés",      "entree": "Secteur Oublié",    "malediction": "faible",     "petra": "La Rive"},
    "cimmerian_garrison":  {"nom": "Garnison Cimmérienne",         "secteur": "Cave de la Lumière Stellaire", "entree": "Secteur Oublié",    "malediction": "croissante", "petra": "Brumes Divaliennes"},
    "ouroborea":           {"nom": "Ouroborea",                    "secteur": "Repos de l'Aphélie",           "entree": "Secteur Oublié",    "malediction": "forte",      "petra": "Sylve de Rhéa"},
    "forfeit_shrine":      {"nom": "Autel du Forfait",             "secteur": "Jardins d'Esila",              "entree": "Exploration Libre", "malediction": "faible",     "petra": "La Rive"},
    "shattered_ruins":     {"nom": "Ruines Brisées",               "secteur": "Crète de Kérès",               "entree": "Exploration Libre", "malediction": "croissante", "petra": "Brumes Divaliennes"},
    "keep_of_honed_edges": {"nom": "Fort des Tranchants Aiguisés", "secteur": "Ermitage de l'Augure",         "entree": "Exploration Libre", "malediction": "forte",      "petra": "Sylve de Rhéa"},
}

# Contrat Petra (hash item, composant 402 VendorSales) → clé de défi.
# COMPLET & vérifié (relevé live + light.gg FR).
CONTRAT_VERS_DEFI: dict[int, str] = {
    3207732940: "agonarch_abyss",       # Abysse des Argonarques
    542328999:  "cimmerian_garrison",   # Garnison Cimmérienne
    3337739523: "ouroborea",            # Ouroborea
    128980839:  "forfeit_shrine",       # Autel du Forfait
    1147672297: "shattered_ruins",      # Ruines Brisées
    2338128705: "keep_of_honed_edges",  # Fort des Tranchants Aiguisés
}

# Nombre de défis À VENIR affichés sous l'actif
# (cycle complet SANS doublon : 6 - 1 = 5).
UPCOMING_COUNT = len(DEFIS_ORDRE) - 1


def image_filename(challenge: str) -> str:
    """Nom de fichier image d'un défi : « <clé>.png ».

    Les clés sont déjà ASCII/snake_case. Images (optionnelles) dans
    Ressources/Ascendant/. Ex. « agonarch_abyss » → « agonarch_abyss.png »."""
    return f"{challenge}.png"
