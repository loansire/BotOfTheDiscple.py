# -*- coding: utf-8 -*-
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BUNGIE_API_KEY = os.getenv("BUNGIE_API_KEY")

# Validation au démarrage : on échoue tôt et clairement
_missing = [
    name
    for name, value in (
        ("DISCORD_TOKEN", DISCORD_TOKEN),
        ("BUNGIE_API_KEY", BUNGIE_API_KEY),
    )
    if not value
]
if _missing:
    raise RuntimeError(
        f"Variable(s) manquante(s) dans le .env : {', '.join(_missing)}"
    )

# --- Chemins transverses (utilisés par les features) ---
BASE_DIR = Path(__file__).resolve().parent.parent
RESOURCES_DIR = BASE_DIR / "Ressources"
ALERTS_DIR = RESOURCES_DIR / "AlertDatabase"
OUTPUT_DIR = BASE_DIR / "Output"