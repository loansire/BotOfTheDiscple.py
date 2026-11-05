# -*- coding: utf-8 -*-
"""Calcul des publications weekly/daily (Components V2, rangées en base).

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

Les builders renvoient des Message (bot/content/model.py) ; la publication
les relit en base (bot/publishing/content_source.py).

Ligne « Prochaine actualisation » : par défaut calculée ici (prochain reset
quotidien pour les secteurs, prochain reset du mardi pour raids/donjons), mais
surchargeable via `next_refresh_unix` pour laisser la pipeline décider.

Cache d'images isolé par feature (cf. banner.py) : les bandeaux secteurs sont
mis en cache sous `banners/secteur_oublie/`, ceux des raids/donjons sous
`banners/raid_donjon/` (cache PARTAGÉ raids+donjons : la purge est orchestrée
une seule fois en amont côté handler)."""
from __future__ import annotations



from bot.bungie.reset import TUESDAY, next_reset, next_weekday_reset
from bot.content.model import Message, button, image, separator, text
from bot.features.weekly.models import ActivityVariant, LostSector, WeeklyActivity
from bot.render.banner import BANNER_RATIO, get_banner

from bot.render.activity_emojis import DJ_EMOJI as _DJ_EMOJI
from bot.render.activity_emojis import RD_EMOJI as _RD_EMOJI
from bot.render.activity_emojis import activity_emoji_for
from bot.render.layout import refresh_line
from bot.render.emotes import e

_ACCENT = 0x992D22  # discord.Color.dark_red()

# Clés de feature pour le cache d'images (cf. banner.py / purge_banner_cache).
# Raids et donjons PARTAGENT le même dossier de cache (purge unique en amont).
_FEATURE_RAID_DUNGEON = "raid_donjon"
_FEATURE_LOST_SECTOR = "secteur_oublie"

# Emojis de titre — ajuste librement (emojis custom serveur acceptés).
_LS_EMOJI = e("topic.lost_sector")

# Emotes des boucliers / champions, par clé telle qu'écrite dans
# lost_sector_extra.json (greffée dans variant.extra).
_EXTRA_EMOJIS = {
    # Boucliers
    "Solaires": e("element.solar"),
    "Abyssaux": e("element.void"),
    "Cryo-électriques": e("element.arc"),
    "Stasiques": e("element.stasis"),
    "Filobscures": e("element.strand"),
    # Champions
    "Brise-bouclier": e("champion.barrier"),
    "Perturbation": e("champion.overload"),
    "Chancellement": e("champion.unstoppable"),
}

# ── Emojis par modificateur d'activité (secteurs oubliés) ──────────────
# hash de modificateur (DestinyActivityModifierDefinition) → emoji custom.
# Sert À LA FOIS de whitelist (seuls les hashes présents sont affichés) et de
# table de traduction en emoji. Le NOM de l'emoji (<:nom:id>) est ignoré par
# Discord au rendu (seul l'id compte) : on l'abrège pour économiser le budget
# de 4000 caractères par message.
_LS_MODIFIER_EMOJIS: dict[int, str] = {
    # Surcharges d'arme.
    95459596: e("mod.surge_hand_cannon"),
    1282934989: e("mod.surge_sniper"),
    2178457119: e("mod.surge_trace"),
    2626834038: e("mod.surge_fusion"),
    2743796883: e("mod.surge_glaive"),
    3132780533: e("mod.surge_pulse"),
    3320777106: e("mod.surge_linear"),
    3758645512: e("mod.surge_gl"),
    795009574: e("mod.surge_machine_gun"),
    1326581064: e("mod.surge_sword"),
    # Surcharges élémentaires.
    426976067: e("mod.surge_solar"),
    2691200658: e("mod.surge_arc"),
    3196075844: e("mod.surge_void"),
    2983647439: e("mod.surge_stasis"),
    3809788899: e("mod.surge_stasis"),
    3810297122: e("mod.surge_strand"),
    # Menaces.
    3517267764: e("mod.threat_solar"),
    186409259: e("mod.threat_arc"),
    3652821947: e("mod.threat_void"),
    512042454: e("mod.threat_stasis"),
    1598472557: e("mod.threat_strand"),
}


def _refresh_line_short(next_refresh_unix: int) -> str:
    """Ligne courte « Actualisation <relatif> » (secteurs oubliés).

    `<t:…:R>` rend déjà « dans X h » : on n'ajoute pas de « Dans » en dur
    (sinon « Actualisation Dans dans X h »)."""
    return f"Actualisation <t:{next_refresh_unix}:R>"


def _activity_emoji(group: WeeklyActivity) -> str:
    """Emoji custom de l'activité, avec fallback générique par type."""
    return activity_emoji_for(group.base_name, group.activity_type)


# ── Raids & Donjons ────────────────────────────────────────────────────

# ⚙️ Limites temporaires (contrainte des 40 composants CV2 par message).
#    Mettre à None pour tout afficher.
_MAX_RAIDS = 99
_MAX_DUNGEONS = 99


async def _add_activities(
    container: Message,
    groups: list[WeeklyActivity],
    ratio: float,
    with_banner: bool = True,
) -> None:
    """Ajoute (par activité) le nom puis, si `with_banner`, le bandeau pgcr recadré.

    Les activités PERMANENTES sont rendues sans bandeau : elles ne changent
    jamais d'une semaine à l'autre, l'image n'apporte donc aucune information
    et coûte une pièce jointe + un composant CV2 par message."""
    for g in groups:
        container.add(text(f"### {_activity_emoji(g)} {g.base_name}"))
        if not with_banner:
            continue
        # pgcr absente ou placeholder → bandeau générique (cf. get_banner).
        banner = await get_banner(g.pgcr_image, _FEATURE_RAID_DUNGEON, ratio)
        if banner:
            fname = f"rd_{sum(c.kind == 'gallery' for c in container.components)}.webp"
            container.add(image("gallery", banner, fname))


async def _build_activity_container(
    title: str,
    rotation: list[WeeklyActivity],
    permanent: list[WeeklyActivity],
    permanent_label: str,
    ratio: float,
) -> Message:
    """Un container : titre, sous-section « En rotation » PUIS sous-section
    permanente (rotation au-dessus). Chaque sous-section : séparateur + en-tête
    + (par activité) nom puis bandeau pgcr."""
    container = Message(accent_color=_ACCENT)
    container.add(text(title))

    if rotation:
        container.add(separator())
        container.add(text("**En rotation**"))
        await _add_activities(container, rotation, ratio)

    if permanent:
        container.add(separator())
        container.add(text(f"**{permanent_label}**"))
        await _add_activities(container, permanent, ratio, with_banner=False)

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
) -> Message:
    """Construit la vue (1 container) pour UN type d'activité (raid OU donjon).

    On n'affiche QUE les activités *featured* de la semaine (challenges actifs,
    farmables) — cf. WeeklyActivity.featured. Repli si rien n'est featured.

    `next_refresh_unix` : timestamp de la prochaine actualisation (défaut =
    prochain reset du mardi, les raids/donjons changeant à l'hebdo)."""
    if next_refresh_unix is None:
        next_refresh_unix = int(next_weekday_reset(TUESDAY).timestamp())
    refresh = refresh_line(next_refresh_unix)

    featured = [g for g in groups if g.featured and g.activity_type == activity_type]
    if max_items is not None:
        featured = featured[:max_items]

    if featured:
        container = await _build_activity_container(
            f"# {title_emoji} {title_label}\n{refresh}",
            [g for g in featured if not g.permanent],
            [g for g in featured if g.permanent],
            permanent_label,
            ratio,
        )
    else:
        # Repli : aucune activité featured détectée → on évite une vue vide.
        container = Message(accent_color=_ACCENT)
        container.add(text(
            f"# {title_emoji} {title_label}\n"
            f"{refresh}\n"
            f"-# {fallback_label}"
        ))

    # Bouton « Rotation prédictive » : custom_id traité par
    # bot/discord/cogs/content_actions.py.
    kind = "dungeon" if activity_type == "Donjon" else "raid"
    container.add(separator())
    container.add(button("Rotation prédictive", f"weekly:rota:{kind}", emoji="🗓️", style="primary"))
    return container


async def build_raid_view(
    groups: list[WeeklyActivity],
    ratio: float = BANNER_RATIO,
    next_refresh_unix: int | None = None,
) -> Message:
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
) -> Message:
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
    return " · ".join(emojis)


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
) -> list[Message]:
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

    messages: list[Message] = []

    for i, sector in enumerate(sectors):
        container = Message(accent_color=_ACCENT)

        # Titre : destination en en-tête (#), nom du secteur (##). PAS de ligne
        # d'actualisation ici — elle est placée en bas, sous l'image.
        if sector.destination:
            header = f"# {_LS_EMOJI} {sector.destination}\n## {sector.base_name}"
        else:
            header = f"# {_LS_EMOJI} {sector.base_name}"
        lines = [header]

        # Ligne d'icônes des modificateurs (commune aux 2 difficultés).
        # Préfixée '## ' (test d'affichage : agrandit les icônes de surges).
        mod_line = _modifier_icons_line(sector)
        if mod_line:
            lines.append(f"## {mod_line}")

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

        container.add(text("\n".join(lines)))

        # pgcr absente ou placeholder → bandeau générique (cf. get_banner).
        banner = await get_banner(sector.pgcr_image, _FEATURE_LOST_SECTOR, ratio)
        if banner:
            container.add(image("gallery", banner, f"ls_{i}.webp"))

        # Ligne d'actualisation (courte), TOUT EN BAS — sous l'image.
        container.add(text(_refresh_line_short(next_refresh_unix)))

        messages.append(container)

    return messages