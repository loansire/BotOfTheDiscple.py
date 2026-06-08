# -*- coding: utf-8 -*-
"""Construit les composants V2 de /botconfig (2 niveaux : accueil / détail)."""
import discord
from discord import ui

from bot.utils.subscriptions import TOPICS
from bot.discord.configbot_components import (
    BackButton,
    ConfigChannelSelect,
    ConfigRoleSelect,
    ResetButton,
    TopicSettingsButton,
    ValidateButton,
)

_ACCENT = discord.Color.dark_red()       # darkred — carte au repos
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


def _summary_text(pending: dict, topic: str, dirty: bool) -> str:
    meta = TOPICS[topic]
    p = pending[topic]
    ch_txt = f"<#{p['channel_id']}>" if p["channel_id"] else "*aucun*"
    role_txt = f"<@&{p['role_id']}>" if p["role_id"] else "*aucun*"
    marker = "  🟠 *(non validé)*" if dirty else ""
    return (
        f"### {meta['emoji']} {meta['label']}{marker}\n"
        f"Salon : {ch_txt}  •  Rôle : {role_txt}"
    )


# ── Page principale ────────────────────────────────────────────────────


def _summary_section(persisted: dict, pending: dict, topic: str) -> ui.Section:
    """Une ligne de résumé + bouton ⚙️ aligné à droite (accessoire)."""
    dirty = _topic_dirty(persisted, pending, topic)
    return ui.Section(
        ui.TextDisplay(_summary_text(pending, topic, dirty)),
        accessory=TopicSettingsButton(topic),
    )


def _build_main_page(persisted: dict, pending: dict) -> list:
    dirty = is_dirty(persisted, pending)
    container = ui.Container(
        ui.TextDisplay(
            "# Configuration des alertes\n"
            "-# Clique sur ⚙️ pour le configurer chaque topic."
        ),
        accent_color=_ACCENT_DIRTY if dirty else _ACCENT,
    )
    for topic in TOPICS:
        container.add_item(ui.Separator())
        container.add_item(_summary_section(persisted, pending, topic))
    return [container]


# ── Page détail (un topic) ─────────────────────────────────────────────


def _action_row(persisted: dict, pending: dict, topic: str) -> ui.ActionRow:
    """Dirty → Valider/Annuler (ramènent à l'accueil) ; sinon → Retour."""
    if _topic_dirty(persisted, pending, topic):
        return ui.ActionRow(ValidateButton(), ResetButton())
    return ui.ActionRow(BackButton())


def _build_topic_page(guild: discord.Guild, persisted: dict, pending: dict, topic: str) -> list:
    p = pending[topic]
    dirty = _topic_dirty(persisted, pending, topic)

    ch_select = ConfigChannelSelect(topic, _resolve_channel(guild, p["channel_id"]))
    role_select = ConfigRoleSelect(
        topic,
        _resolve_role(guild, p["role_id"]),
        disabled=p["channel_id"] is None,
    )

    return [
        ui.TextDisplay("# ⚙️ Configuration des alertes"),
        ui.Separator(),
        ui.Container(
            ui.TextDisplay(_summary_text(pending, topic, dirty)),
            ui.ActionRow(ch_select),
            ui.ActionRow(role_select),
            _action_row(persisted, pending, topic),
            accent_color=_ACCENT_DIRTY if dirty else _ACCENT,
        ),
    ]


# ── Aiguillage ─────────────────────────────────────────────────────────


def build_config_components(
    guild: discord.Guild, persisted: dict, pending: dict, current_topic: str | None
) -> list:
    """Renvoie la liste de composants top-level selon la page courante."""
    if current_topic is None:
        return _build_main_page(persisted, pending)
    return _build_topic_page(guild, persisted, pending, current_topic)