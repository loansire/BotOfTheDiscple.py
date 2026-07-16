# -*- coding: utf-8 -*-
"""Construit les composants V2 de /botconfig (navigation multi-pages).

Arbre déclaratif NAV_TREE (aplati) :
- racine          → Sections « jeu » (aperçu + flèche ➡️)
- jeu             → Sections « catégorie » (aperçu + flèche ➡️)  /  ou feuille
- feuille (`topics`) → Sections « topic » (résumé salon/rôle + ⚙️), paginée

Chaque page a un TITRE en fil d'Ariane des 2 derniers niveaux (`parent · courant`,
emoji compris) ; la racine n'apparaît jamais comme miette. En descendant d'un
cran, la fenêtre du fil d'Ariane glisse (le grand-parent disparaît).

Les Sections de navigation portent un aperçu AUTO des options qu'elles
contiennent (libellés des sous-sections, ou noms courts `short` des topics).

La navigation reste toujours « propre » : dès qu'un topic est modifié (pending ≠
persisted), seuls Valider/Annuler sont proposés sur sa page détail (aucun bouton
de navigation), donc le staging ne peut pas s'échapper."""
import discord
from discord import ui

from bot.utils.subscriptions import TOPICS
from bot.discord.configbot_components import (
    BackButton,
    ConfigChannelSelect,
    ConfigRoleSelect,
    NavButton,
    NextPageButton,
    PrevPageButton,
    ResetButton,
    TopicSettingsButton,
    ValidateButton,
)

_ACCENT = discord.Color.dark_red()       # carte au repos
_ACCENT_DIRTY = 0xF0A30A                  # orange — topic modifié non validé

ROOT = "root"

# Topics par page dans une feuille. Au-delà → pagination (◀️ ▶️). Marge sous la
# limite Discord (40 composants/message) : 7 + 4×N ≤ 40 tient jusqu'à N=8.
_TOPICS_PER_PAGE = 6


# ── Arbre de navigation ────────────────────────────────────────────────
# Chaque nœud : `title` (racine seulement), `label`/`emoji` (identité du nœud —
# repris dans les Sections et le fil d'Ariane), et soit `children` (nœuds fils),
# soit `topics` (clés de topics). L'ordre des listes = l'ordre d'affichage.
# ⚙️ Les emojis des sections (⚔️/🛒/📰) sont modifiables ici (emojis custom OK).
NAV_TREE: dict[str, dict] = {
    ROOT: {
        "title": "Configuration des alertes",
        "children": ["game_destiny", "game_marathon"],
    },
    "game_destiny": {
        "label": "Destiny 2",
        "emoji": "<:D2:1270042220627497020>",
        "children": ["sec_activites", "sec_vendeurs", "sec_articles"],
    },
    "sec_activites": {
        "label": "Rotations Activités",
        "emoji": "",
        "topics": ["weekly_raid", "weekly_dungeon", "daily_lost_sector"],
    },
    "sec_vendeurs": {
        "label": "Rotations Vendeurs",
        "emoji": "",
        "topics": ["ada", "eververse", "xur"],
    },
    "sec_articles": {
        "label": "Articles",
        "emoji": "",
        "topics": ["news_patch_note", "news_twid", "maintenance_destiny"],
    },
    "game_marathon": {
        "label": "Marathon",
        "emoji": "<:Marathon:1513347065881559273>",
        "topics": ["maintenance_marathon"],
    },
}

# Cartes dérivées (parent d'un nœud ; feuille parente d'un topic).
_PARENT: dict[str, str] = {}
_TOPIC_LEAF: dict[str, str] = {}
for _nid, _node in NAV_TREE.items():
    for _child in _node.get("children", []):
        _PARENT[_child] = _nid
    for _topic in _node.get("topics", []):
        _TOPIC_LEAF[_topic] = _nid


def _parent_of(node_id: str) -> str | None:
    """Nœud parent (None pour la racine). Un topic → sa feuille parente."""
    if node_id.startswith("topic:"):
        return _TOPIC_LEAF.get(node_id.split(":", 1)[1])
    return _PARENT.get(node_id)


def _display(node_id: str) -> tuple[str, str]:
    """(emoji, label) d'un nœud ou d'un topic ("topic:<t>")."""
    if node_id.startswith("topic:"):
        meta = TOPICS[node_id.split(":", 1)[1]]
        return meta.get("emoji", ""), meta["label"]
    node = NAV_TREE[node_id]
    return node.get("emoji", ""), node.get("label", node.get("title", ""))


def _page_title(node_id: str) -> str:
    """Fil d'Ariane des 2 derniers niveaux (`parent · courant`), emoji compris.

    La racine n'est jamais une miette : si le parent est la racine (ou absent),
    on n'affiche que le nœud courant."""
    if node_id == ROOT:
        return NAV_TREE[ROOT]["title"]
    cur_e, cur_l = _display(node_id)
    cur = f"{cur_e} {cur_l}".strip()
    parent = _parent_of(node_id)
    if parent is None or parent == ROOT:
        return cur
    par_e, par_l = _display(parent)
    return f"{par_e} {par_l} · {cur}".strip()


def _preview(node_id: str) -> str:
    """Aperçu auto des options : libellés des sous-sections, ou noms courts
    (`short`) des topics."""
    node = NAV_TREE[node_id]
    if "children" in node:
        return " · ".join(NAV_TREE[c]["label"] for c in node["children"])
    return " · ".join(TOPICS[t].get("short", TOPICS[t]["label"]) for t in node.get("topics", []))


# ── Helpers communs ─────────────────────────────────────────────────────


def _resolve_channel(guild: discord.Guild, cid: str | None):
    return guild.get_channel_or_thread(int(cid)) if cid else None


def _resolve_role(guild: discord.Guild, rid: str | None):
    return guild.get_role(int(rid)) if rid else None


def _topic_dirty(persisted: dict, pending: dict, topic: str) -> bool:
    per, pen = persisted[topic], pending[topic]
    return per["channel_id"] != pen["channel_id"] or per["role_id"] != pen["role_id"]


def _status_text(pending: dict, topic: str, dirty: bool) -> str:
    """Ligne d'état salon/rôle (sans en-tête) pour la page détail."""
    p = pending[topic]
    ch = f"<#{p['channel_id']}>" if p["channel_id"] else "*aucun*"
    role = f"<@&{p['role_id']}>" if p["role_id"] else "*aucun*"
    marker = "  🟠 *(non validé)*" if dirty else ""
    return f"Salon : {ch}  •  Rôle : {role}{marker}"


def _summary_text(pending: dict, topic: str, dirty: bool) -> str:
    """En-tête topic (emoji + libellé + marqueur) + ligne d'état, pour les
    Sections de feuille."""
    e, l = _display(f"topic:{topic}")
    marker = "  🟠 *(non validé)*" if dirty else ""
    p = pending[topic]
    ch = f"<#{p['channel_id']}>" if p["channel_id"] else "*aucun*"
    role = f"<@&{p['role_id']}>" if p["role_id"] else "*aucun*"
    return f"### {e} {l}{marker}\nSalon : {ch}  •  Rôle : {role}"


# ── Sections ─────────────────────────────────────────────────────────────


def _nav_section(child_id: str) -> ui.Section:
    """Section de navigation : titre + aperçu auto, flèche ➡️ en accessoire."""
    e, l = _display(child_id)
    return ui.Section(
        ui.TextDisplay(f"### {e} {l}\n-# {_preview(child_id)}"),
        accessory=NavButton(child_id),
    )


def _summary_section(persisted: dict, pending: dict, topic: str) -> ui.Section:
    """Section de topic : résumé salon/rôle, ⚙️ en accessoire."""
    dirty = _topic_dirty(persisted, pending, topic)
    return ui.Section(
        ui.TextDisplay(_summary_text(pending, topic, dirty)),
        accessory=TopicSettingsButton(topic),
    )


# ── Page liste (nav OU feuille — même structure) ────────────────────────


def _build_list_page(persisted: dict, pending: dict, node_id: str, page: int) -> list:
    node = NAV_TREE[node_id]
    is_nav = "children" in node
    entries = node["children"] if is_nav else node["topics"]

    total_pages = max(1, (len(entries) + _TOPICS_PER_PAGE - 1) // _TOPICS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * _TOPICS_PER_PAGE
    page_entries = entries[start:start + _TOPICS_PER_PAGE]

    suffix = f"  ·  page {page + 1}/{total_pages}" if total_pages > 1 else ""
    container = ui.Container(
        ui.TextDisplay(f"# {_page_title(node_id)}{suffix}"),
        accent_color=_ACCENT,
    )

    # Un séparateur AVANT chaque entrée (divise aussi sous le titre).
    for entry in page_entries:
        container.add_item(ui.Separator())
        if is_nav:
            container.add_item(_nav_section(entry))
        else:
            container.add_item(_summary_section(persisted, pending, entry))

    if total_pages > 1:
        container.add_item(ui.Separator())
        container.add_item(ui.ActionRow(
            PrevPageButton(disabled=page == 0),
            NextPageButton(disabled=page >= total_pages - 1),
        ))

    parent = _parent_of(node_id)
    if parent is not None:
        container.add_item(ui.ActionRow(BackButton(parent)))
    return [container]


# ── Page détail (un topic) ──────────────────────────────────────────────


def _action_row(persisted: dict, pending: dict, topic: str) -> ui.ActionRow:
    """Dirty → Valider/Annuler ; sinon → Retour (vers la feuille parente)."""
    return_node = _TOPIC_LEAF.get(topic, ROOT)
    if _topic_dirty(persisted, pending, topic):
        return ui.ActionRow(ValidateButton(return_node), ResetButton(return_node))
    return ui.ActionRow(BackButton(return_node))


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
        ui.Container(
            ui.TextDisplay(f"# {_page_title(f'topic:{topic}')}"),
            ui.Separator(),
            ui.TextDisplay(_status_text(pending, topic, dirty)),
            ui.ActionRow(ch_select),
            ui.ActionRow(role_select),
            _action_row(persisted, pending, topic),
            accent_color=_ACCENT_DIRTY if dirty else _ACCENT,
        ),
    ]


# ── Aiguillage ─────────────────────────────────────────────────────────


def build_config_components(
    guild: discord.Guild, persisted: dict, pending: dict,
    node_id: str = ROOT, page: int = 0,
) -> list:
    """Renvoie la liste de composants top-level selon la page courante."""
    if node_id.startswith("topic:"):
        topic = node_id.split(":", 1)[1]
        if topic in TOPICS:
            return _build_topic_page(guild, persisted, pending, topic)
        node_id = ROOT  # topic inconnu → repli racine

    if node_id not in NAV_TREE:
        node_id = ROOT

    return _build_list_page(persisted, pending, node_id, page)