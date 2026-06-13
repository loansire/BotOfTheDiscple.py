# -*- coding: utf-8 -*-
"""Setup OAuth Bungie — À LANCER UNE FOIS À LA MAIN.

Usage :
    python -m scripts.xur_oauth_setup
    (ou : python scripts/xur_oauth_setup.py depuis la racine du projet)

Déroulé :
1. Le script affiche l'URL d'autorisation Bungie.
2. Tu l'ouvres dans un navigateur (connecté au compte du bot) et tu autorises.
3. Bungie redirige vers https://localhost/callback?code=XXXX&state=...
   La page ne chargera pas (aucun serveur local) — c'est NORMAL.
   Copie la valeur du paramètre `code` depuis la barre d'adresse.
4. Colle ce code ici. Le script l'échange contre les tokens et les écrit dans
   le fichier de tokens (refresh_token persisté pour le runtime).

Le refresh_token reste valide ~90 jours (glissants) : tant que le bot tourne
et rafraîchit régulièrement, tu n'as pas à relancer ce script. S'il expire,
relance-le simplement.
"""
import asyncio
import sys
from pathlib import Path

# Permet `python scripts/xur_oauth_setup.py` depuis la racine.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.bungie.oauth import (  # noqa: E402
    TOKENS_PATH,
    authorize_url,
    exchange_code,
)


def _extract_code(raw: str) -> str:
    """Accepte soit le code brut, soit l'URL de redirection complète collée."""
    raw = raw.strip()
    if "code=" in raw:
        # URL complète collée → on isole le paramètre code.
        after = raw.split("code=", 1)[1]
        return after.split("&", 1)[0]
    return raw


async def main() -> int:
    print("=" * 70)
    print("  Setup OAuth Bungie — BotOfTheDisciple")
    print("=" * 70)
    print("\n1) Ouvre cette URL dans un navigateur (compte du bot) et autorise :\n")
    print(f"   {authorize_url()}\n")
    print("2) Après autorisation, Bungie redirige vers :")
    print("   https://localhost/callback?code=XXXX&state=...")
    print("   La page ne chargera PAS (pas de serveur local) — c'est normal.")
    print("   Copie le `code` (ou colle l'URL complète ci-dessous).\n")

    raw = input("Code (ou URL de redirection) > ").strip()
    code = _extract_code(raw)
    if not code:
        print("\n[ERREUR] Aucun code fourni. Abandon.")
        return 1

    print("\n→ Échange du code contre les tokens…")
    try:
        tokens = await exchange_code(code)
    except Exception as e:
        print(f"\n[ERREUR] Échange échoué : {e}")
        return 1

    print("\n✅ Tokens enregistrés avec succès.")
    print(f"   Fichier : {TOKENS_PATH}")
    print(f"   membership_id : {tokens.get('membership_id')}")
    print("\n⚠️  Ajoute ce fichier à ton .gitignore (il contient un secret).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))