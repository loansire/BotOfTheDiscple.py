# -*- coding: utf-8 -*-
"""État persistant anti-spam, par jeu (compute_state, clés `maintenance.<jeu>`)."""
from bot.storage.compute_state import compute_state


class MaintenanceState:
    def get(self, game: str) -> dict:
        return dict(compute_state.get(f"maintenance.{game}", {}))

    def set(self, game: str, state: dict):
        compute_state.set(f"maintenance.{game}", state)

    async def save(self) -> None:
        await compute_state.save()
