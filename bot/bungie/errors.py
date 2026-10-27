# -*- coding: utf-8 -*-
"""Erreurs Bungie + détection de la maintenance / des indisponibilités.

Deux familles d'erreurs « à retenter », toutes deux sous BungieUnavailableError
(c'est elle que la pipeline intercepte pour entrer en « hold mode » : ne pas
avancer l'état du reset et retenter plus tard) :

- BungieMaintenanceError : maintenance DÉCLARÉE (503 / SystemDisabled).
- BungieNotReadyError    : panne NON déclarée (5xx, 429, throttling, corps
  illisible, erreur réseau) OU données manifestement pas prêtes (périmées,
  incomplètes juste après un reset).

Les prédicats sont purs (aucune dépendance réseau) → testables isolément."""
from __future__ import annotations

from typing import Optional


class BungieUnavailableError(RuntimeError):
    """Données Bungie indisponibles pour le moment : à retenter plus tard."""


class BungieMaintenanceError(BungieUnavailableError):
    """L'API Bungie est en maintenance.

    Observé sous deux formes :
    - HTTP 503 au niveau transport (ex. log réel :
      « HTTP 503 | SystemDisabled (This system is temporarily disabled…) »)
    - HTTP 200 enveloppant ErrorStatus='SystemDisabled' / ErrorCode=5
    """


class BungieNotReadyError(BungieUnavailableError):
    """Panne transitoire non déclarée, ou données pas encore à jour."""


# ErrorCode Bungie pour SystemDisabled.
SYSTEM_DISABLED_CODE = 5

# ErrorStatus de throttling : l'API répond, mais refuse temporairement.
_THROTTLE_STATUSES = {
    "DestinyThrottledByGameServer",
    "ThrottleLimitExceeded",
    "ThrottleLimitExceededMinutes",
    "ThrottleLimitExceededMomentarily",
    "ThrottleLimitExceededSeconds",
    "PerApplicationThrottleExceeded",
    "PerApplicationAnonymousThrottleExceeded",
    "PerApplicationAuthenticatedThrottleExceeded",
    "PerUserThrottleExceeded",
    "PerEndpointRequestThrottleExceeded",
}

# ErrorStatus DÉFINITIFS : retenter ne changera rien (Bungie masque certains
# d'entre eux en HTTP 500, d'où la liste explicite).
_PERMANENT_STATUSES = {
    "ApiInvalidOrExpiredKey",
    "ApiKeyMissingFromRequest",
    "InsufficientPrivileges",
    "AccessNotPermittedByApplicationScope",
    "DestinyAccountNotFound",
    "DestinyCharacterNotFound",
    "DestinyPrivacyRestriction",
    "DestinyComponentNotFound",
    "DestinyItemNotFound",
    "DestinyVendorNotFound",
    "WebAuthRequired",
}


def is_maintenance(
    status_code: Optional[int] = None,
    err_status: Optional[str] = None,
    err_code: Optional[int] = None,
) -> bool:
    """True si la réponse traduit une maintenance Bungie.

    Un 503 vaut toujours « indisponible → réessayer » (peu importe la raison).
    Sinon, on s'appuie sur l'enveloppe Bungie (ErrorStatus / ErrorCode)."""
    if status_code == 503:
        return True
    if err_status == "SystemDisabled":
        return True
    if err_code == SYSTEM_DISABLED_CODE:
        return True
    return False


def is_transient(
    status_code: Optional[int] = None,
    err_status: Optional[str] = None,
    body_readable: bool = True,
) -> bool:
    """True si l'échec est probablement temporaire (à retenter plus tard).

    À appeler APRÈS is_maintenance. Throttling → transitoire. Un ErrorStatus
    connu comme définitif → jamais transitoire, même sous un HTTP 500. Sinon :
    5xx, 429, ou corps illisible (page HTML d'un proxy) → transitoire."""
    if err_status in _THROTTLE_STATUSES:
        return True
    if err_status in _PERMANENT_STATUSES:
        return False
    if status_code is not None and (status_code >= 500 or status_code == 429):
        return True
    return not body_readable
