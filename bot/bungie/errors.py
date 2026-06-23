# -*- coding: utf-8 -*-
"""Erreurs Bungie + détection de la maintenance.

BungieMaintenanceError est levée par le client quand l'API est temporairement
indisponible pour maintenance. La pipeline l'intercepte pour entrer en « hold
mode » : ne pas avancer l'état du reset et retenter au poll suivant (chaque
minute) jusqu'au rétablissement.

`is_maintenance` est un prédicat pur (aucune dépendance réseau) → testable
isolément contre des payloads réels."""
from __future__ import annotations

from typing import Optional


class BungieMaintenanceError(RuntimeError):
    """L'API Bungie est en maintenance.

    Observé sous deux formes :
    - HTTP 503 au niveau transport (ex. log réel :
      « HTTP 503 | SystemDisabled (This system is temporarily disabled…) »)
    - HTTP 200 enveloppant ErrorStatus='SystemDisabled' / ErrorCode=5
    """


# ErrorCode Bungie pour SystemDisabled.
SYSTEM_DISABLED_CODE = 5


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
