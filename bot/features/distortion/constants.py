# -*- coding: utf-8 -*-
"""Constantes de la feature Distorsion (co-localisées).

Rotation FIXE de 7 destinations, une par heure. Aucune dépendance API : tout se
calcule à partir d'une unique ancre temporelle (cf. __init__.py).

Principe de centralisation minimale : seules des constantes SPÉCIFIQUES à cette
feature vivent ici (rien n'est partagé avec d'autres scripts)."""
import unicodedata

# Emoji d'en-tête de la publication (topic « distortion »).
DISTORTION_EMOJI = "<:Distortion:1533753753772097596>"

# Ordre FIXE du cycle (index 0 = destination active à l'ANCRE).
ORDER: tuple[str, ...] = (
    "Cité des Rêves",
    "Monde Trône de Savathûn",
    "Lune",
    "Europe",
    "Nessos",
    "Cosmodrome",
    "Zone Morte Européenne",
)

# Nombre de destinations À VENIR affichées sous l'active
# (cycle complet SANS doublon : 7 - 1 = 6).
UPCOMING_COUNT = len(ORDER) - 1


def image_filename(destination: str) -> str:
    """Nom de fichier image d'une destination : ASCII, espaces → « _ », .png.

    Ex. « Cité des Rêves » → « Cite_des_Reves.png ». Les images vivent dans
    Ressources/Distortion/."""
    ascii_name = (
        unicodedata.normalize("NFKD", destination)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return ascii_name.replace(" ", "_") + ".png"
