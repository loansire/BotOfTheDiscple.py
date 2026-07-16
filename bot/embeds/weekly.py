# -*- coding: utf-8 -*-
"""Rendu Components V2 des activités weekly/daily.

- Raids & Donjons : chaque type a SON propre builder (et donc son propre message
  persistant), liste des noms + bandeau pgcr recadré par activité, séparateurs.
  Chaque nom est précédé de son emoji custom (résolu par nom normalisé, fallback
  générique sinon).
- Secteurs perdus : UN MESSAGE PAR SECTEUR (build_lost_sectors_view renvoie une
  liste). Chaque message : destination en en-tête (###), nom du secteur en gras
  dessous, sa propre ligne d'actualisation, la ligne d'icônes des modificateurs
  (commune aux deux difficultés), le texte (boucliers/champions par difficulté)
  PUIS le bandeau pgcr recadré. Ce découpage évite la limite Discord de 4000
  caractères de texte cumulé par message (CV2).

Les builders raid/donjon renvoient (LayoutView, fichiers). Le builder secteurs
renvoie une LISTE de (LayoutView, fichiers). La publication (post/édition) est
gérée ailleurs.

Ligne « Prochaine actualisation » : par défaut calculée ici (prochain reset
quotidien pour les secteurs, prochain reset du mardi pour raids/donjons), mais
surchargeable via `next_refresh_unix` pour laisser la pipeline décider.

Cache d'images isolé par feature (cf. banner.py) : les bandeaux secteurs sont
mis en cache sous `banners/secteur_oublie/`, ceux des raids/donjons sous
`banners/raid_donjon/` (cache PARTAGÉ raids+donjons : la purge est orchestrée
une seule fois en amont côté handler)."""
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
# Raids et donjons PARTAGENT le même dossier de cache (purge unique en amont).
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
    "Solaires": "<:So:1270714993553178624>",
    "Abyssaux": "<:Ab:1270715025660711023>",
    "Cryo-électriques": "<:Cr:1270715011781627904>",
    "Stasiques": "<:St:1293381064869285938>",
    "Filobscures": "<:Fi:1293381094774931456>",
    # Champions
    "Brise-bouclier": "<:Bl:1270042102033678388>",
    "Perturbation": "<:Su:1270042140944236619>",
    "Chancellement": "<:Im:1270042120857849877>",
}

# ── Emojis par modificateur d'activité (secteurs oubliés) ──────────────
# hash de modificateur (DestinyActivityModifierDefinition) → emoji custom.
# Sert À LA FOIS de whitelist (seuls les hashes présents sont affichés) et de
# table de traduction en emoji. Le NOM de l'emoji (<:nom:id>) est ignoré par
# Discord au rendu (seul l'id compte) : on l'abrège pour économiser le budget
# de 4000 caractères par message.
_LS_MODIFIER_EMOJIS: dict[int, str] = {
    # Surcharges d'arme.
    95459596: "<:s_LR:1527291256999383060>",
    1282934989: "<:s_FDP:1527291249705357343>",
    2178457119: "<:s_FAR:1527291248094875711>",
    2626834038: "<:s_FAF:1527291245632815105>",
    2743796883: "<:s_G:1527291252477923469>",
    3132780533: "<:s_FAP:1527291246987706489>",
    3320777106: "<:s_FAFL:1527291250917507163>",
    3758645512: "<:s_LG:1527291257980846271>",
    795009574: "<:s_M:1527291259130220695>",
    1326581064: "<:s_E:1527291244525654076>",
    # Surcharges élémentaires.
    426976067: "<:s_S:1527290822595444856>",
    2691200658: "<:s_C:1527290821307662456>",
    3196075844: "<:s_A:1527290819831140413>",
    2983647439: "<:s_St:1527290823912194128>",
    3809788899: "<:s_St:1527290823912194128>",
    3810297122: "<:s_F:1527291156256526558>",
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
    "Désert perpétuel (Épique)": "<:DP:1399391431302451300>",
}

_DUNGEON_EMOJIS_RAW = {
    "Fosse de l'Hérésie": "<:Fosse:1275104301827620865>",
    "Prophétie": "<:Prophetie:1275104326854901852>",
    "Trône Brisé": "<:Trone:1275104381242572873>",
    "Etreinte de l'Avarice": "<:Etreinte:1275104223016517742>",
    "Dualité": "<:Dualite:1275104177143676948>",
    "Flèche de la Vigie": "<:Fleche:1275104276347359385>",
    "Fantômes des Profondeurs": "<:Fantome:1275104249700941844>",
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
    """Ligne « Actualisation: <date> (dans …) »."""
    return (
        f"Actualisation: <t:{next_refresh_unix}:F> "
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
_MAX_RAIDS = 99
_MAX_DUNGEONS = 99


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


async def _build_single_type_view(
    groups: list[WeeklyActivity],
    *,
    activity_type: str,
    title_emoji: str,
    title_label: str,
    permanent_label: str,
    fallback_label: str,
    max_items: int | None,
    ratio: float,
    next_refresh_unix: int | None,
) -> tuple[WeeklyView, list[discord.File]]:
    """Construit la vue (1 container) pour UN type d'activité (raid OU donjon).

    On n'affiche QUE les activités *featured* de la semaine (challenges actifs,
    farmables) — cf. WeeklyActivity.featured. Repli si rien n'est featured.

    `next_refresh_unix` : timestamp de la prochaine actualisation (défaut =
    prochain reset du mardi, les raids/donjons changeant à l'hebdo)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_weekday_reset(TUESDAY).timestamp())
    refresh = _refresh_line(next_refresh_unix)

    featured = [g for g in groups if g.featured and g.activity_type == activity_type]
    if max_items is not None:
        featured = featured[:max_items]

    files: list[discord.File] = []

    if featured:
        container = await _build_activity_container(
            f"# {title_emoji} {title_label}\n{refresh}",
            [g for g in featured if not g.permanent],
            [g for g in featured if g.permanent],
            permanent_label,
            files, ratio,
        )
    else:
        # Repli : aucune activité featured détectée → on évite une vue vide.
        container = ui.Container(accent_color=_ACCENT)
        container.add_item(ui.TextDisplay(
            f"# {title_emoji} {title_label}\n"
            f"{refresh}\n"
            f"-# {fallback_label}"
        ))

    return WeeklyView(container), files


async def build_raid_view(
    groups: list[WeeklyActivity],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> tuple[WeeklyView, list[discord.File]]:
    """Vue (1 message) des raids featured de la semaine."""
    return await _build_single_type_view(
        groups,
        activity_type="Raid",
        title_emoji=_RD_EMOJI,
        title_label="Raids de la semaine",
        permanent_label="Raid permanent",
        fallback_label="Aucun raid featured détecté pour le moment.",
        max_items=_MAX_RAIDS,
        ratio=ratio,
        next_refresh_unix=next_refresh_unix,
    )


async def build_dungeon_view(
    groups: list[WeeklyActivity],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> tuple[WeeklyView, list[discord.File]]:
    """Vue (1 message) des donjons featured de la semaine."""
    return await _build_single_type_view(
        groups,
        activity_type="Donjon",
        title_emoji=_DJ_EMOJI,
        title_label="Donjons de la semaine",
        permanent_label="Donjon permanent",
        fallback_label="Aucun donjon featured détecté pour le moment.",
        max_items=_MAX_DUNGEONS,
        ratio=ratio,
        next_refresh_unix=next_refresh_unix,
    )


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


def _modifier_icons_line(sector: LostSector) -> str | None:
    """Ligne d'icônes des modificateurs, COMMUNE aux deux difficultés.

    Union des `modifier_hashes` de toutes les variantes (dédupliquée, dans
    l'ordre de première apparition), filtrée aux hashes connus de
    _LS_MODIFIER_EMOJIS. Renvoie 'emoji | emoji | …' ou None si aucun
    modificateur connu."""
    seen: set[int] = set()
    emojis: list[str] = []
    for variant in sector.variants:
        for h in variant.modifier_hashes:
            if h in _LS_MODIFIER_EMOJIS and h not in seen:
                seen.add(h)
                emojis.append(_LS_MODIFIER_EMOJIS[h])
    if not emojis:
        return None
    return " | ".join(emojis)


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
) -> list[tuple[WeeklyView, list[discord.File]]]:
    """Renvoie une LISTE de (vue, fichiers) : UN message par secteur.

    Chaque message : destination en en-tête (###), nom du secteur en gras
    dessous, sa propre ligne d'actualisation, la ligne d'icônes des
    modificateurs (commune aux difficultés), les lignes par difficulté
    (boucliers/champions en emotes), puis le bandeau recadré.

    `next_refresh_unix` : timestamp de la prochaine actualisation (défaut =
    prochain reset quotidien, les secteurs changeant chaque jour). Affiché
    identiquement sur chaque message."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_reset().timestamp())

    messages: list[tuple[WeeklyView, list[discord.File]]] = []

    for i, sector in enumerate(sectors):
        container = ui.Container(accent_color=_ACCENT)

        # Titre : destination en en-tête (###), nom du secteur en gras dessous.
        if sector.destination:
            header = f"### {_LS_EMOJI} {sector.destination}\n**{sector.base_name}**"
        else:
            header = f"### {_LS_EMOJI} {sector.base_name}"
        # Ligne d'actualisation propre à ce message.
        header += f"\n{_refresh_line(next_refresh_unix)}"
        lines = [header]

        # Ligne d'icônes des modificateurs (commune aux 2 difficultés).
        mod_line = _modifier_icons_line(sector)
        if mod_line:
            lines.append(mod_line)

        # Lignes par difficulté (boucliers/champions greffés).
        variant_lines = []
        for variant in sector.variants:
            line = _format_variant_line(variant)
            if line:
                variant_lines.append(line)

        if variant_lines:
            lines.extend(variant_lines)
        else:
            # Repli : aucune donnée greffée → on liste au moins les difficultés.
            diffs = " · ".join(v.label for v in sector.variants)
            if diffs:
                lines.append(diffs)

        container.add_item(ui.TextDisplay("\n".join(lines)))

        files: list[discord.File] = []
        if sector.pgcr_image:
            banner = await get_banner(sector.pgcr_image, _FEATURE_LOST_SECTOR, ratio)
            if banner:
                fname = f"ls_{i}.webp"
                files.append(discord.File(BytesIO(banner), filename=fname))
                container.add_item(
                    ui.MediaGallery(discord.MediaGalleryItem(f"attachment://{fname}"))
                )

        messages.append((WeeklyView(container), files))

    return messages