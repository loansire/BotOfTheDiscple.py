# -*- coding: utf-8 -*-
"""Rendu Components V2 des activités weekly/daily.

- Raids & Donjons : deux containers (Raids puis Donjons), liste des noms +
  bandeau pgcr recadré par activité, séparateurs. Chaque nom est précédé de
  son emoji custom (résolu par nom normalisé, fallback générique sinon).
- Secteurs perdus : une carte par secteur, texte (boucliers/champions par
  difficulté) PUIS bandeau pgcr recadré.

Les builders renvoient une LayoutView et la liste des fichiers à joindre.
La publication (post/édition) est gérée ailleurs.

Ligne « Prochaine actualisation » : par défaut calculée ici (prochain reset
quotidien pour les secteurs, prochain reset du mardi pour raids/donjons), mais
surchargeable via `next_refresh_unix` pour laisser la pipeline décider.

Cache d'images isolé par feature (cf. banner.py) : les bandeaux secteurs sont
mis en cache sous `banners/secteur_oublie/`, ceux des raids/donjons sous
`banners/raid_donjon/`."""
from __future__ import annotations

import unicodedata
from io import BytesIO

import discord
from discord import ui

from bot.bungie.reset import TUESDAY, next_reset, next_weekday_reset
from bot.embeds.banner import BANNER_RATIO, get_banner
from bot.features.weekly.models import ActivityVariant, LostSector, WeeklyActivity

_ACCENT = discord.Color.dark_red()

# Clés de feature pour le cache d'images (cf. banner.py / purge_banner_cache).
_FEATURE_RAID_DUNGEON = "raid_donjon"
_FEATURE_LOST_SECTOR = "secteur_oublie"

# Emojis de titre — ajuste librement (emojis custom serveur acceptés).
_RD_EMOJI = "<:Raid:1338595321319788595>"
_DJ_EMOJI = "<:Donjon:1338595321319788595>"
_LS_EMOJI = "<:Secteur:1270042203577778246>"

# Emotes des boucliers / champions, par clé telle qu'écrite dans
# lost_sector_extra.json (greffée dans variant.extra).
_EXTRA_EMOJIS = {
    # Boucliers
    "Solaires": "<:Solaire:1270714993553178624>",
    "Abyssaux": "<:Abyssale:1270715025660711023>",
    "Cryo-électriques": "<:Cryo:1270715011781627904>",
    "Stasiques": "<:Stase:1293381064869285938>",
    "Filobscures": "<:Filobscur:1293381094774931456>",
    # Champions
    "Brise-bouclier": "<:Bloqueur:1270042102033678388>",
    "Perturbation": "<:Surcharge:1270042140944236619>",
    "Chancellement": "<:Implacable:1270042120857849877>",
}

# ── Emojis par activité (raids & donjons) ──────────────────────────────
# Clés telles qu'utilisées côté communauté ; le matching se fait sur la
# forme NORMALISÉE (cf. _norm_name) pour absorber les écarts avec le
# manifest Bungie (article initial « Le/La », ligature œ, accents).
_RAID_EMOJIS_RAW = {
    "Dernier Voeu": "<:LW:1273058036209946634>",
    "Jardin du Salut": "<:JDS:1273058012751335486>",
    "Crypte de la Pierre": "<:DSC:1273057991670890496>",
    "Caveau de verre": "<:VOG:1273058120192495658>",
    "Serment du Disciple": "<:VOW:1273058146453295155>",
    "Chute du Roi": "<:Oryx:1273058059849302056>",
    "Origine des Cauchemars": "<:RON:1273058080086560870>",
    "Chute de Cropta": "<:Cropta:1273057968660676790>",
    "Orée du Salut": "<:SE:1273058098818322492>",
    "Désert Perpétuel": "<:DP:1399391431302451300>",
}

_DUNGEON_EMOJIS_RAW = {
    "Fosse de l'Hérésie": "<:Fosse:1275104301827620865>",
    "Prophétie": "<:Prophetie:1275104326854901852>",
    "Trône Brisé": "<:Trone:1275104381242572873>",
    "Etreinte de l'Avarice": "<:Etreinte:1275104223016517742>",
    "Dualité": "<:Dualite:1275104177143676948>",
    "Flèche de la Vigie": "<:Fleche:1275104276347359385>",
    "Fantôme des Profondeurs": "<:Fantome:1275104249700941844>",
    "Ruine de la Guerrière": "<:Ruine:1275104356387000450>",
    "Hôte Vesper": "<:Vesper:1295144736964870214>",
    "Dogme fragmenté": "<:Dogme:1341339537221353492>",
    "Équilibre": "<:Equilibre:1513709145348509726>",
}


def _norm_name(name: str) -> str:
    """Normalise un nom d'activité pour un matching tolérant.

    - ligature œ/Œ → 'oe' (NFKD ne la décompose pas)
    - minuscules, retrait de l'article initial (le/la/les/l')
    - suppression des accents (NFKD + filtrage des diacritiques)
    """
    s = name.replace("œ", "oe").replace("Œ", "OE").replace("\u0153", "oe")
    s = s.strip().lower()
    for art in ("le ", "la ", "les ", "l'"):
        if s.startswith(art):
            s = s[len(art):]
            break
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip()


# Dicts résolus une fois, par forme normalisée.
_RAID_EMOJIS = {_norm_name(k): v for k, v in _RAID_EMOJIS_RAW.items()}
_DUNGEON_EMOJIS = {_norm_name(k): v for k, v in _DUNGEON_EMOJIS_RAW.items()}


def _refresh_line(next_refresh_unix: int) -> str:
    """Ligne « Prochaine actualisation le <date> (dans …) »."""
    return (
        f"Prochaine actualisation le <t:{next_refresh_unix}:F> "
        f"(<t:{next_refresh_unix}:R>)"
    )


def _activity_emoji(group: WeeklyActivity) -> str:
    """Emoji custom de l'activité, avec fallback générique par type."""
    key = _norm_name(group.base_name)
    if group.activity_type == "Donjon":
        return _DUNGEON_EMOJIS.get(key, _DJ_EMOJI)
    return _RAID_EMOJIS.get(key, _RD_EMOJI)


class WeeklyView(ui.LayoutView):
    """LayoutView persistante (non interactive)."""

    def __init__(self, *children: ui.Item):
        super().__init__(timeout=None)
        for child in children:
            self.add_item(child)


# ── Raids & Donjons ────────────────────────────────────────────────────

# ⚙️ Limites temporaires (contrainte des 40 composants CV2 par message).
#    Mettre à None pour tout afficher.
_MAX_RAIDS = 4
_MAX_DUNGEONS = 3


async def _add_activities(
    container: ui.Container,
    groups: list[WeeklyActivity],
    files: list[discord.File],
    ratio: float,
) -> None:
    """Ajoute (par activité) le nom puis le bandeau pgcr recadré au container."""
    for g in groups:
        container.add_item(ui.TextDisplay(f"### {_activity_emoji(g)} {g.base_name}"))
        if g.pgcr_image:
            banner = await get_banner(g.pgcr_image, _FEATURE_RAID_DUNGEON, ratio)
            if banner:
                fname = f"rd_{len(files)}.webp"
                files.append(discord.File(BytesIO(banner), filename=fname))
                container.add_item(
                    ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}"))
                )


async def _build_activity_container(
    title: str,
    rotation: list[WeeklyActivity],
    permanent: list[WeeklyActivity],
    permanent_label: str,
    files: list[discord.File],
    ratio: float,
) -> ui.Container:
    """Un container : titre, sous-section « En rotation » PUIS sous-section
    permanente (rotation au-dessus). Chaque sous-section : séparateur + en-tête
    + (par activité) nom puis bandeau pgcr."""
    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(title))

    if rotation:
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay("**En rotation**"))
        await _add_activities(container, rotation, files, ratio)

    if permanent:
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"**{permanent_label}**"))
        await _add_activities(container, permanent, files, ratio)

    return container


async def build_raid_dungeon_view(
    groups: list[WeeklyActivity],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> tuple[WeeklyView, list[discord.File]]:
    """Deux containers (Raids puis Donjons), chacun avec liste + bandeaux.

    On n'affiche QUE les activités *featured* de la semaine (challenges actifs,
    farmables) — cf. WeeklyActivity.featured.

    `next_refresh_unix` : timestamp de la prochaine actualisation (défaut =
    prochain reset du mardi, les raids/donjons changeant à l'hebdo)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_weekday_reset(TUESDAY).timestamp())
    refresh = _refresh_line(next_refresh_unix)

    featured = [g for g in groups if g.featured]
    raids = [g for g in featured if g.activity_type == "Raid"]
    dungeons = [g for g in featured if g.activity_type == "Donjon"]

    if _MAX_RAIDS is not None:
        raids = raids[:_MAX_RAIDS]
    if _MAX_DUNGEONS is not None:
        dungeons = dungeons[:_MAX_DUNGEONS]

    files: list[discord.File] = []
    children: list[ui.Item] = []

    if raids:
        children.append(await _build_activity_container(
            f"# {_RD_EMOJI} Raids de la semaine\n{refresh}",
            [g for g in raids if not g.permanent],
            [g for g in raids if g.permanent],
            "Raid permanent",
            files, ratio,
        ))
    if dungeons:
        children.append(await _build_activity_container(
            f"# {_DJ_EMOJI} Donjons de la semaine\n{refresh}",
            [g for g in dungeons if not g.permanent],
            [g for g in dungeons if g.permanent],
            "Donjon permanent",
            files, ratio,
        ))

    # Repli : aucune activité featured détectée → on évite une vue vide.
    if not children:
        fallback = ui.Container(accent_color=_ACCENT)
        fallback.add_item(ui.TextDisplay(
            f"# {_RD_EMOJI} Raids & Donjons de la semaine\n"
            f"{refresh}\n"
            "-# Aucune activité featured détectée pour le moment."
        ))
        children.append(fallback)

    return WeeklyView(*children), files


# ── Secteurs perdus ────────────────────────────────────────────────────


def _emote_group(values: dict, sep: str = " ") -> str:
    """'{Abyssaux: 11, ...}' → '<:emote:…>11 <:emote:…>2'.
    Ignore les clés sans emote connue."""
    parts = []
    for key, n in values.items():
        emote = _EXTRA_EMOJIS.get(key)
        if emote:
            parts.append(f"{emote}{n}")
    return sep.join(parts)


def _format_variant_line(variant: ActivityVariant) -> str | None:
    """Ligne d'une difficulté : '**Maîtrise** - … · …', ou None si
    aucune donnée greffée."""
    extra = variant.extra or {}
    shields = _emote_group(extra.get("shields", {}))
    champs = _emote_group(extra.get("champions", {}))

    segments = []
    if shields:
        segments.append(f"{shields}")
    if champs:
        segments.append(f"{champs}")
    if not segments:
        return None

    return f"**{variant.label}**\n" + "  |  ".join(segments)


async def build_lost_sectors_view(
    sectors: list[LostSector],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> tuple[WeeklyView, list[discord.File]]:
    """Renvoie (vue, fichiers). Chaque secteur : titre, lignes par difficulté
    (boucliers/champions en emotes), puis bandeau recadré.

    `next_refresh_unix` : timestamp de la prochaine actualisation (défaut =
    prochain reset quotidien, les secteurs changeant chaque jour)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())

    container = ui.Container(accent_color=_ACCENT)
    container.add_item(ui.TextDisplay(
        f"# {_LS_EMOJI} Secteurs Oubliés du jour\n"
        f"{_refresh_line(next_refresh_unix)}"
    ))

    files: list[discord.File] = []
    for i, sector in enumerate(sectors):
        container.add_item(ui.Separator())

        dest = f" · {sector.destination}" if sector.destination else ""
        lines = [f"### {sector.base_name}{dest}"]

        for variant in sector.variants:
            line = _format_variant_line(variant)
            if line:
                lines.append(line)

        # Repli : si aucune donnée greffée, on liste au moins les difficultés.
        if len(lines) == 1:
            diffs = " · ".join(v.label for v in sector.variants)
            if diffs:
                lines.append(diffs)

        container.add_item(ui.TextDisplay("\n".join(lines)))

        if sector.pgcr_image:
            banner = await get_banner(sector.pgcr_image, _FEATURE_LOST_SECTOR, ratio)
            if banner:
                fname = f"ls_{i}.webp"
                files.append(discord.File(BytesIO(banner), filename=fname))
                container.add_item(
                    ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}"))
                )

    return WeeklyView(container), files