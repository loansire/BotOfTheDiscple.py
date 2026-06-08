# -*- coding: utf-8 -*-
"""Construit les composants V2 de /botconfig (une 'carte' Container par topic)."""
import discord
from discord import ui

from bot.utils.subscriptions import TOPICS
from bot.discord.configbot_components import ConfigChannelSelect, ConfigRoleSelect

_ACCENT = 0x5865F2        # blurple — carte au repos
_ACCENT_DIRTY = 0xF0A30A  # orange — carte modifiée non validée


def _resolve_channel(guild: discord.Guild, cid: str | None):
    return guild.get_channel_or_thread(int(cid)) if cid else None


def _resolve_role(guild: discord.Guild, rid: str | None):
    return guild.get_role(int(rid)) if rid else None


def _topic_dirty(persisted: dict, pending: dict, topic: str) -> bool:
    per, pen = persisted[topic], pending[topic]
    return per["channel_id"] != pen["channel_id"] or per["role_id"] != pen["role_id"]


def is_dirty(persisted: dict, pending: dict) -> bool:
    """True si au moins un topic diffère de l'état persisté."""
    return any(_topic_dirty(persisted, pending, t) for t in TOPICS)


def _card(guild: discord.Guild, persisted: dict, pending: dict, topic: str) -> ui.Container:
    meta = TOPICS[topic]
    p = pending[topic]
    dirty = _topic_dirty(persisted, pending, topic)

    ch_txt = f"<#{p['channel_id']}>" if p["channel_id"] else "*aucun*"
    role_txt = f"<@&{p['role_id']}>" if p["role_id"] else "*aucun*"
    marker = "  🟠 *(non validé)*" if dirty else ""
    header = (
        f"### {meta['emoji']} {meta['label']}{marker}\n"
        f"Salon : {ch_txt}  •  Rôle : {role_txt}"
    )

    ch_select = ConfigChannelSelect(topic, _resolve_channel(guild, p["channel_id"]))
    role_select = ConfigRoleSelect(
        topic,
        _resolve_role(guild, p["role_id"]),
        disabled=p["channel_id"] is None,
    )

    return ui.Container(
        ui.TextDisplay(header),
        ui.ActionRow(ch_select),
        ui.ActionRow(role_select),
        accent_color=_ACCENT_DIRTY if dirty else _ACCENT,
    )


def build_config_components(guild: discord.Guild, persisted: dict, pending: dict) -> list:
    """Renvoie la liste de composants top-level (hors boutons Valider/Annuler)."""
    comps: list = [
        ui.TextDisplay(
            "# ⚙️ Configuration des alertes\n"
            "-# Un salon et un rôle (optionnel) par type d'alerte. "
            "Les changements ne s'appliquent qu'après **Valider**."
        )
    ]
    for topic in TOPICS:
        comps.append(_card(guild, persisted, pending, topic))
    return comps
