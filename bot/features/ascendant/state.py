# -*- coding: utf-8 -*-
"""État persistant des messages Défis ascendants (un message par serveur abonné).

On NE persiste PAS le défi actif (recalculable à tout instant depuis l'ancre).
On persiste seulement, par serveur : l'id du message publié et un `hash`
identifiant la semaine actuellement affichée. Si le hash stocké diffère de la
semaine courante → le message est édité (avance d'un cran). Ce mécanisme assure
aussi le rattrapage automatique après une coupure du bot.

Schéma (Ressources/AlertDatabase/ascendant_state.json) :
    { "<guild_id>": { "message_id": "<id>" | null, "hash": "<str>" | null } }
"""
import json

from bot.config import ALERTS_DIR
from bot.utils.logger import log

STORE_PATH = ALERTS_DIR / "ascendant_state.json"


class AscendantMessageState:
    def __init__(self):
        self._data: dict = self._load()

    def _load(self) -> dict:
        if STORE_PATH.exists():
            try:
                with open(STORE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                log.warning(f"[Ascendant] Lecture de l'état échouée : {e}")
        return {}

    def save(self) -> None:
        ALERTS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            log.error(f"[Ascendant] Écriture de l'état échouée : {e}")

    def get(self, guild_id) -> dict:
        """Entrée d'un serveur ({message_id, hash}), valeurs None si absent."""
        return self._data.get(str(guild_id), {"message_id": None, "hash": None})

    def set(self, guild_id, *, message_id, content_hash) -> None:
        self._data[str(guild_id)] = {
            "message_id": str(message_id),
            "hash": content_hash,
        }

    def purge(self, guild_id) -> None:
        """Oublie l'état d'un serveur (retrait du salon)."""
        self._data.pop(str(guild_id), None)

    def invalidate(self) -> None:
        """Efface les hash (conserve les message_id) → force une ré-édition au
        prochain publish. Le caller appelle save()."""
        for entry in self._data.values():
            entry["hash"] = None
