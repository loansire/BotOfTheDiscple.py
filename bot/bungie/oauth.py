# -*- coding: utf-8 -*-
"""OAuth Bungie (Authorization Code grant, client Confidential).

Certains endpoints (GetVendor → Xûr) exigent un token utilisateur : la seule
X-API-Key renvoie ErrorCode 12 (InsufficientPrivileges, masqué en HTTP 500).

Flux :
- Une fois à la main (scripts/xur_oauth_setup.py) : on échange un code
  d'autorisation contre access_token + refresh_token, persistés sur disque.
- Au runtime : get_access_token() renvoie un access_token valide, le
  rafraîchissant via le refresh_token si expiré. Le refresh_token est
  lui-même régénéré à chaque refresh (~90 j glissants) et re-persisté.

Le fichier de tokens contient un secret de longue durée → à ajouter au
.gitignore (cf. TOKENS_PATH).
"""
from __future__ import annotations

import json
import time
from base64 import b64encode

import aiohttp

from bot.config import BUNGIE_CLIENT_ID, BUNGIE_CLIENT_SECRET, MANIFEST_DIR
from bot.utils.logger import log

TOKEN_URL = "https://www.bungie.net/Platform/App/OAuth/token/"
AUTHORIZE_URL = "https://www.bungie.net/en/OAuth/Authorize"

# Secret de longue durée — à exclure du versionnage (.gitignore).
TOKENS_PATH = MANIFEST_DIR / "bungie_tokens.json"

# Marge de sécurité : on rafraîchit un peu avant l'expiration réelle.
_EXPIRY_MARGIN = 60  # secondes


class OAuthError(RuntimeError):
    """Erreur d'authentification OAuth (token manquant/expiré/échec refresh)."""


def _basic_auth_header() -> dict:
    """Header Authorization Basic client_id:client_secret (client Confidential)."""
    raw = f"{BUNGIE_CLIENT_ID}:{BUNGIE_CLIENT_SECRET}".encode("utf-8")
    return {"Authorization": f"Basic {b64encode(raw).decode('ascii')}"}


def _load_tokens() -> dict:
    if TOKENS_PATH.exists():
        with open(TOKENS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_tokens(data: dict) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _store_response(payload: dict) -> dict:
    """Normalise une réponse token Bungie → dict persistable (timestamps absolus).

    Bungie renvoie expires_in / refresh_expires_in (secondes relatives) ;
    on les convertit en instants absolus pour un contrôle simple au runtime."""
    now = int(time.time())
    tokens = {
        "access_token": payload["access_token"],
        "access_expires": now + int(payload.get("expires_in", 3600)),
        "refresh_token": payload.get("refresh_token"),
        "refresh_expires": now + int(payload.get("refresh_expires_in", 7776000)),
        "membership_id": payload.get("membership_id"),
    }
    _save_tokens(tokens)
    return tokens


async def exchange_code(code: str) -> dict:
    """Échange un code d'autorisation contre les tokens (setup initial).

    Appelé par le script de setup, pas au runtime."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
    }
    return await _post_token(data)


async def _refresh(refresh_token: str) -> dict:
    """Rafraîchit l'access_token à partir d'un refresh_token."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    return await _post_token(data)


async def _post_token(data: dict) -> dict:
    """POST vers l'endpoint token Bungie (Basic auth + form-urlencoded)."""
    if not BUNGIE_CLIENT_ID or not BUNGIE_CLIENT_SECRET:
        raise OAuthError(
            "BUNGIE_CLIENT_ID / BUNGIE_CLIENT_SECRET manquants dans le .env."
        )
    headers = _basic_auth_header()
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    async with aiohttp.ClientSession() as session:
        async with session.post(TOKEN_URL, data=data, headers=headers) as resp:
            body = await resp.json(content_type=None)
            if resp.status != 200:
                raise OAuthError(
                    f"Échange token échoué (HTTP {resp.status}) : "
                    f"{body.get('error_description') or body}"
                )
    return _store_response(body)


async def get_access_token() -> str:
    """Renvoie un access_token valide, en rafraîchissant si nécessaire.

    Raises:
        OAuthError: si aucun token n'est présent (setup jamais fait) ou si le
        refresh_token a expiré (relancer le script de setup)."""
    tokens = _load_tokens()
    if not tokens.get("access_token"):
        raise OAuthError(
            "Aucun token Bungie. Lance d'abord scripts/xur_oauth_setup.py."
        )

    now = int(time.time())
    if now < tokens.get("access_expires", 0) - _EXPIRY_MARGIN:
        return tokens["access_token"]

    # access_token expiré → refresh
    refresh_token = tokens.get("refresh_token")
    if not refresh_token or now >= tokens.get("refresh_expires", 0):
        raise OAuthError(
            "Refresh token expiré ou absent. Relance scripts/xur_oauth_setup.py."
        )

    log.info("[OAuth] Rafraîchissement de l'access_token Bungie.")
    new_tokens = await _refresh(refresh_token)
    return new_tokens["access_token"]


def authorize_url(state: str = "botofthedisciple") -> str:
    """URL d'autorisation à ouvrir dans un navigateur (setup initial)."""
    return (
        f"{AUTHORIZE_URL}?client_id={BUNGIE_CLIENT_ID}"
        f"&response_type=code&state={state}"
    )