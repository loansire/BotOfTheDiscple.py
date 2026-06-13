# -*- coding: utf-8 -*-
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BUNGIE_API_KEY = os.getenv("BUNGIE_API_KEY")

# Personnage Destiny 2 de référence (compte du bot) servant à lire les
# rotations weekly/daily. Les rotations étant globales, un seul perso suffit.
BUNGIE_MEMBERSHIP_TYPE = os.getenv("BUNGIE_MEMBERSHIP_TYPE")
BUNGIE_MEMBERSHIP_ID = os.getenv("BUNGIE_MEMBERSHIP_ID")
BUNGIE_CHARACTER_ID = os.getenv("BUNGIE_CHARACTER_ID")

# Identifiants OAuth (client Confidential) — requis UNIQUEMENT pour les
# endpoints authentifiés (GetVendor → Xûr). Volontairement OPTIONNELS : le bot
# démarre sans eux ; seule la feature Xûr loggue une erreur si elle tourne sans
# tokens. Le refresh_token n'est PAS ici (il change à chaque refresh) : il vit
# dans bungie_tokens.json, géré par bot/bungie/oauth.py.
BUNGIE_CLIENT_ID = os.getenv("BUNGIE_CLIENT_ID")
BUNGIE_CLIENT_SECRET = os.getenv("BUNGIE_CLIENT_SECRET")

# Validation au démarrage : on échoue tôt et clairement
_missing = [
    name
    for name, value in (
        ("DISCORD_TOKEN", DISCORD_TOKEN),
        ("BUNGIE_API_KEY", BUNGIE_API_KEY),
        ("BUNGIE_MEMBERSHIP_TYPE", BUNGIE_MEMBERSHIP_TYPE),
        ("BUNGIE_MEMBERSHIP_ID", BUNGIE_MEMBERSHIP_ID),
        ("BUNGIE_CHARACTER_ID", BUNGIE_CHARACTER_ID),
    )
    if not value
]
if _missing:
    raise RuntimeError(
        f"Variable(s) manquante(s) dans le .env : {', '.join(_missing)}"
    )

# Regroupé pour un usage pratique dans le client Bungie.
BUNGIE_CHARACTER = {
    "membership_type": BUNGIE_MEMBERSHIP_TYPE,
    "membership_id": BUNGIE_MEMBERSHIP_ID,
    "character_id": BUNGIE_CHARACTER_ID,
}

# --- Chemins transverses (utilisés par les features) ---
BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "Ressources"
ALERTS_DIR = RESOURCES_DIR / "AlertDatabase"
OUTPUT_DIR = BASE_DIR / "Output"

# Cache local des données Bungie (manifest + activités personnage).
# Réutilisé par toutes les features qui résolvent des hashes hors-ligne.
MANIFEST_DIR = RESOURCES_DIR / "Manifest"