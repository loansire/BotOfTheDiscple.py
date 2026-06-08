# -*- coding: utf-8 -*-
"""Mise en forme Discord + extraction de la fenêtre de maintenance."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

OFFLINE_TRIGGER = "brought offline for expected maintenance"
ONLINE_TRIGGER = "be able to log back"

GAME_EMOJIS = {
    "destiny": "<\\:destlogo:710283624619966484>",
    "marathon": "<\\:marathon:1111270580923142164>",
}
GAME_LABELS = {
    "destiny": "Destiny 2",
    "marathon": "Marathon",
}


def _iso_to_unix(iso_str: str) -> int:
    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _find_step(event: dict, trigger: str) -> Optional[dict]:
    for step in event.get("steps", []):
        for detail in step.get("details", []):
            if trigger in detail.lower():
                return step
    return None


def offline_iso(event: dict) -> Optional[str]:
    """ISO 8601 du step de mise hors ligne, ou None."""
    step = _find_step(event, OFFLINE_TRIGGER)
    return step.get("time_utc") if step else None


def extract_window(data: dict) -> Optional[dict]:
    """Première maintenance avec un step offline daté → dict structuré pour l'embed."""
    for event in data.get("events", []):
        off = _find_step(event, OFFLINE_TRIGGER)
        if not off or not off.get("time_utc"):
            continue
        on = _find_step(event, ONLINE_TRIGGER)
        return {
            "game": data["game"],
            "game_label": GAME_LABELS.get(data["game"], data["game"].title()),
            "event_type": event.get("event_type"),
            "offline_iso": off["time_utc"],
            "offline_unix": _iso_to_unix(off["time_utc"]),
            "online_unix": _iso_to_unix(on["time_utc"]) if on and on.get("time_utc") else None,
        }
    return None


def format_discord_message(data: dict) -> str | None:
    """Texte prêt à copier-coller (peut couvrir plusieurs événements)."""
    messages: list[str] = []
    for event in data.get("events", []):
        off = _find_step(event, OFFLINE_TRIGGER)
        if off is None or not off.get("time_utc"):
            continue
        on = _find_step(event, ONLINE_TRIGGER)
        off_unix = _iso_to_unix(off["time_utc"])

        emoji = GAME_EMOJIS.get(data["game"], "🎮")
        label = GAME_LABELS.get(data["game"], data["game"].title())

        lines = [f"{emoji} __**Maintenance {label}**__ du <t:{off_unix}:D>:"]
        lines.append(f"- :pencil:: {event.get('event_type', '')}")
        ret_part = ""
        if on and on.get("time_utc"):
            ret_part = f" | :white_check_mark: Retour serv <t:{_iso_to_unix(on['time_utc'])}:t>"
        lines.append(
            f":x: Arrêt serv <t:{off_unix}:t>{ret_part}"
            f" | :repeat: Débute: __**<t:{off_unix}:R>**__"
        )
        messages.append("\n".join(lines))

    return "\n\n".join(messages) if messages else None