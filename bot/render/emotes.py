# -*- coding: utf-8 -*-
"""Dictionnaire UNIQUE des emotes custom, par bot.

Les emotes sont des emotes d'APPLICATION : chacune n'est utilisable que par
l'app qui la possède. Chaque emote a donc un id par bot, sur une seule ligne :
clé → (nom, id live, id lite).

Fonctionnement :
- le code (calcul, presenters, constantes) n'écrit jamais `<:nom:id>` en dur :
  il appelle `e("clé")`, qui renvoie un marqueur `{e:clé}` ;
- ces marqueurs sont stockés tels quels en base (content_component), donc le
  contenu calculé et son hash sont identiques pour tous les bots ;
- au moment d'envoyer, `resolve()` remplace chaque marqueur par l'emote du bot
  courant (BOT_ID). Appelé par bot/render/components.py pour le contenu
  stocké, et directement par l'UI live (/botconfig).

Clé absente pour le bot courant → chaîne vide + warning dans le log (une seule
fois par clé), jamais de marqueur brut sur Discord.

Ajouter une emote : une ligne dans EMOTES (id None pour un bot qui ne l'a pas
encore), puis `e("clé")` dans le code. Emote animée : nom préfixé « a: »."""
from __future__ import annotations

import re

from bot.core.config import BOT_ID
from bot.core.logger import log

# Une ligne par emote : clé → (nom, id live, id lite). None = pas d'emote
# pour ce bot (omise + warning). Emote animée : nom préfixé « a: ».
BOTS = ("live", "lite")  # ordre des colonnes d'id

EMOTES: dict[str, tuple[str, int | None, int | None]] = {
    # ── Jeux / topics ───────────────────────────────────────────────
    "game.destiny":             ("D2",                  1270042220627497020, None),
    "game.marathon":            ("Marathon",            1513347065881559273, None),
    "topic.lost_sector":        ("Secteur",             1270042203577778246, None),
    "topic.raid":               ("Raid",                1338595321319788595, None),
    "topic.dungeon":            ("Donjon",              1338595206706233458, None),
    "topic.xur":                ("Xur",                 1527021351368659205, None),
    "topic.eververse":          ("Tess",                1527021352245268675, None),
    "topic.ada":                ("Ada",                 1527021353591374024, None),
    "topic.distortion":         ("Distortion",          1533753753772097596, None),
    "topic.ascendant":          ("Challenge_Ascendant", 1534163534970093618, None),
    "topic.avant_garde":        ("avantgarde",          1568012693108031679, None),
    # ── Monnaies / divers ───────────────────────────────────────────
    "currency.glimmer":         ("Glimer",              1526889023963136030, None),
    "currency.dust":            ("Dust",                1526717375833964626, None),
    "currency.strange_coins":   ("PiecesEtranges",      1516155586755166338, None),
    "misc.craftable":           ("Souvenance",          1528569980226895892, None),
    "misc.blank":               ("Blank",               1516201087944757258, None),
    # ── Loot table : type d'activité ────────────────────────────────
    "loot.prestige":            ("prestige",            1539655055358173324, None),
    "loot.destination":         ("destination",         1539655053814796319, None),
    # ── Raids ───────────────────────────────────────────────────────
    "raid.lw":                  ("LW",                  1273058036209946634, None),
    "raid.gos":                 ("JDS",                 1273058012751335486, None),
    "raid.dsc":                 ("DSC",                 1273057991670890496, None),
    "raid.vog":                 ("VOG",                 1273058120192495658, None),
    "raid.vow":                 ("VOW",                 1273058146453295155, None),
    "raid.kf":                  ("Oryx",                1273058059849302056, None),
    "raid.ron":                 ("RON",                 1273058080086560870, None),
    "raid.crota":               ("Cropta",              1273057968660676790, None),
    "raid.se":                  ("SE",                  1273058098818322492, None),
    "raid.desert":              ("DP",                  1399391431302451300, None),
    # ── Donjons ─────────────────────────────────────────────────────
    "dungeon.pit":              ("Fosse",               1275104301827620865, None),
    "dungeon.prophecy":         ("Prophetie",           1275104326854901852, None),
    "dungeon.shattered_throne": ("Trone",               1275104381242572873, None),
    "dungeon.grasp":            ("Etreinte",            1275104223016517742, None),
    "dungeon.duality":          ("Dualite",             1275104177143676948, None),
    "dungeon.spire":            ("Fleche",              1275104276347359385, None),
    "dungeon.ghosts":           ("Fantome",             1275104249700941844, None),
    "dungeon.warlords_ruin":    ("Ruine",               1275104356387000450, None),
    "dungeon.vesper":           ("Vesper",              1295144736964870214, None),
    "dungeon.sundered_doctrine":("Dogme",               1341339537221353492, None),
    "dungeon.equilibrium":      ("Equilibre",           1513709145348509726, None),
    # ── Types d'arme ────────────────────────────────────────────────
    "weapon.auto_rifle":        ("Fusilautomatique",    1305317622266462238, None),
    "weapon.shotgun":           ("Fusilapompe",         1305317574585745408, None),
    "weapon.machine_gun":       ("Mitrailleuse",        1305317781029388378, None),
    "weapon.hand_cannon":       ("Revolver",            1305317829653823608, None),
    "weapon.rocket_launcher":   ("Lanceroquettes",      1305317762712735744, None),
    "weapon.fusion_rifle":      ("Fusion",              1305317671889403925, None),
    "weapon.sniper_rifle":      ("Fusildeprecision",    1305317655221375026, None),
    "weapon.pulse_rifle":       ("Fusilaimpulsion",     1305317558748057661, None),
    "weapon.scout_rifle":       ("Fusildeclaireur",     1305317638158942248, None),
    "weapon.sidearm":           ("Pistolet",            1305317796908892160, None),
    "weapon.sword":             ("Epee",                1305317544684556370, None),
    "weapon.linear_fusion":     ("Fusionlineaire",      1305317687894999060, None),
    "weapon.heavy_gl":          ("Lancegrenadeslourd",  1305317747349000192, None),
    "weapon.special_gl":        ("Lancegrenadesleger",  1305317726125948968, None),
    "weapon.smg":               ("Pistoletmitrailleur", 1305317813094711416, None),
    "weapon.trace_rifle":       ("Fusilarayon",         1305317604839264257, None),
    "weapon.bow":               ("Arc",                 1305317528079437955, None),
    "weapon.glaive":            ("Glaive",              1305317709751259147, None),
    # ── Éléments (aussi boucliers des secteurs oubliés) ─────────────
    "element.kinetic":          ("Ci",                  1353052017278320650, None),
    "element.arc":              ("Cr",                  1270715011781627904, None),
    "element.solar":            ("So",                  1270714993553178624, None),
    "element.void":             ("Ab",                  1270715025660711023, None),
    "element.stasis":           ("St",                  1293381064869285938, None),
    "element.strand":           ("Fi",                  1293381094774931456, None),
    # ── Munitions ───────────────────────────────────────────────────
    "ammo.primary":             ("Principale",          1352409012511051799, None),
    "ammo.special":             ("Speciale",            1352409042538070016, None),
    "ammo.heavy":               ("Lourde",              1352409107273093191, None),
    # ── Champions ───────────────────────────────────────────────────
    "champion.barrier":         ("Bl",                  1270042102033678388, None),
    "champion.overload":        ("Su",                  1270042140944236619, None),
    "champion.unstoppable":     ("Im",                  1270042120857849877, None),
    # ── Modificateurs de secteurs oubliés : surcharges d'arme ───────
    "mod.surge_hand_cannon":    ("s_LR",                1527291256999383060, None),
    "mod.surge_sniper":         ("s_FDP",               1527291249705357343, None),
    "mod.surge_trace":          ("s_FAR",               1527291248094875711, None),
    "mod.surge_fusion":         ("s_FAF",               1527291245632815105, None),
    "mod.surge_glaive":         ("s_G",                 1527291252477923469, None),
    "mod.surge_pulse":          ("s_FAP",               1527291246987706489, None),
    "mod.surge_linear":         ("s_FAFL",              1527291250917507163, None),
    "mod.surge_gl":             ("s_LG",                1527291257980846271, None),
    "mod.surge_machine_gun":    ("s_M",                 1527291259130220695, None),
    "mod.surge_sword":          ("s_E",                 1527291244525654076, None),
    # ── Modificateurs : surcharges élémentaires ─────────────────────
    "mod.surge_solar":          ("s_S",                 1527290822595444856, None),
    "mod.surge_arc":            ("s_C",                 1527290821307662456, None),
    "mod.surge_void":           ("s_A",                 1527290819831140413, None),
    "mod.surge_stasis":         ("s_St",                1527290823912194128, None),
    "mod.surge_strand":         ("s_F",                 1527291156256526558, None),
    # ── Modificateurs : menaces ─────────────────────────────────────
    "mod.threat_solar":         ("M_S",                 1293381139687276584, None),
    "mod.threat_arc":           ("M_C",                 1293381109173977088, None),
    "mod.threat_void":          ("M_A",                 1293381121400115220, None),
    "mod.threat_stasis":        ("M_St",                1293381159274811505, None),
    "mod.threat_strand":        ("M_F",                 1293381169391468604, None),
}

_TOKEN = re.compile(r"\{e:([a-z0-9_.]+)\}")
_warned: set[tuple[str, str]] = set()


def e(key: str) -> str:
    """Marqueur d'emote, résolu à l'envoi par `resolve()`."""
    if key not in EMOTES:
        raise KeyError(f"Emote inconnue : {key!r} (cf. bot/render/emotes.py)")
    return "{e:" + key + "}"


def _emote(key: str, bot_id: str) -> str:
    name, *ids = EMOTES[key]
    emote_id = ids[BOTS.index(bot_id)] if bot_id in BOTS else None
    if emote_id:
        return f"<{name}:{emote_id}>" if name.startswith("a:") else f"<:{name}:{emote_id}>"
    if (bot_id, key) not in _warned:
        _warned.add((bot_id, key))
        log.warning(f"[Emotes] Clé « {key} » absente pour le bot « {bot_id} » : emote omise.")
    return ""


def resolve(text: str | None, bot_id: str = BOT_ID) -> str | None:
    """Remplace les marqueurs `{e:clé}` par les emotes du bot `bot_id`."""
    if not text or "{e:" not in text:
        return text
    return _TOKEN.sub(lambda m: _emote(m.group(1), bot_id), text)
