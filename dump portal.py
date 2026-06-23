# -*- coding: utf-8 -*-
"""Dump v5 : recherche une activité par NOM dans availableActivities, SANS
filtre isFocusedActivity.

Motivation : « Berceau du mal » (alerte de l'Avant-garde) n'apparaît jamais
dans les focus, alors qu'elle est importante. On veut savoir si elle est
seulement présente dans le profil (mais non-focus), et comment la reconnaître.

Le script :
- balaie TOUTES les availableActivities (pas de filtre focus) ;
- matche par nom normalisé (tolérant casse/accents/œ) sur des mots-clés ;
- pour chaque correspondance, dumpe hash/type/place/dest/isFocused/traits ;
- affiche aussi le node racine « Vanguard Alerts » des constantes globales
  (vanguardAlertsFireteamFinderActivityGraphRootNodeHash), pour recoupement.

Les définitions parentes (famille/trait) ne sont PAS nécessaires ici : on
reste sur ce qui est en cache local + le profil. Seules les constantes
globales sont retéléchargées (singleton léger).

Lancer depuis la racine :  python Dump_find_activity.py
Écrit dump_find_activity.json + résumé console.
"""
import asyncio
import json
import unicodedata

from bot.bungie.client import bungie
from bot.bungie.manifest import manifest

# Mots-clés de recherche (au moins UN doit matcher le nom normalisé).
# On ratisse large pour ne pas rater une variante de nommage manifest.
_KEYWORDS = ["berceau", "alerte", "avant-garde", "avant garde", "vanguard"]

_GLOBAL_DEF = "DestinyGlobalConstantsDefinition"


def _norm(s: str) -> str:
    """Normalise : œ→oe, minuscules, sans accents."""
    s = (s or "").replace("œ", "oe").replace("Œ", "OE").replace("\u0153", "oe")
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _name(d) -> str | None:
    return (d or {}).get("displayProperties", {}).get("name")


def _matches(name: str) -> bool:
    n = _norm(name)
    return any(_norm(kw) in n for kw in _KEYWORDS)


async def main():
    await manifest.sync()

    # Constantes globales (pour le node racine Vanguard Alerts).
    index = await bungie.get_manifest_index("fr")
    vanguard_alert_node = None
    if index is not None:
        _, paths = index
        gpath = paths.get(_GLOBAL_DEF)
        if gpath:
            gdef = await bungie.download_definition(gpath)
            if gdef:
                entry = next(iter(gdef.values()), {})
                vanguard_alert_node = entry.get(
                    "vanguardAlertsFireteamFinderActivityGraphRootNodeHash"
                )

    data = await bungie.get_character_activities(force=True)
    if not data:
        print("ÉCHEC fetch profil")
        return

    acts = data.get("activities", {}).get("data", {}).get("availableActivities", [])

    matches = []
    for a in acts:
        ah = a.get("activityHash")
        adef = manifest.resolve(ah, "DestinyActivityDefinition")
        name = _name(adef) or ""
        if not _matches(name):
            continue

        th = adef.get("activityTypeHash")
        tname = _name(manifest.resolve(th, "DestinyActivityTypeDefinition"))
        place = _name(manifest.resolve(adef.get("placeHash"), "DestinyPlaceDefinition"))
        dest = _name(manifest.resolve(adef.get("destinationHash"), "DestinyDestinationDefinition"))

        matches.append({
            "activityHash": ah,
            "name": name,
            "type": tname,
            "typeHash": th,
            "place": place,
            "destination": dest,
            "isFocusedActivity": bool(a.get("isFocusedActivity")),
            "isVisible": a.get("isVisible"),
            "isNew": a.get("isNew"),
            "canJoin": a.get("canJoin"),
            "canLead": a.get("canLead"),
            "challenges_count": len(a.get("challenges", []) or []),
            "traitHashes": adef.get("traitHashes", []),
            "activityFamilyHashes": adef.get("activityFamilyHashes", []),
        })

    out = {
        "total_availableActivities": len(acts),
        "keywords": _KEYWORDS,
        "vanguardAlertsFireteamFinderActivityGraphRootNodeHash": vanguard_alert_node,
        "match_count": len(matches),
        "matches": matches,
    }
    with open("dump_find_activity.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # ── Résumé console ──────────────────────────────────────────────────
    print(f"availableActivities totales : {len(acts)}")
    print(f"vanguardAlerts…RootNodeHash : {vanguard_alert_node}")
    print(f"correspondances (mots-clés {_KEYWORDS}) : {len(matches)}\n")

    if not matches:
        print("⚠️  AUCUNE correspondance dans availableActivities.")
        print("    → l'activité n'est pas exposée ici ; elle vit probablement")
        print("      dans un autre composant ou un graph node non listé.")
        return

    for m in matches:
        focus = "FOCUS" if m["isFocusedActivity"] else "non-focus"
        print(f"  [{focus}] {m['name']}")
        print(f"      hash={m['activityHash']} | type={m['type']} | "
              f"place={m['place']} | dest={m['destination']}")
        print(f"      visible={m['isVisible']} new={m['isNew']} "
              f"join={m['canJoin']} lead={m['canLead']} "
              f"challenges={m['challenges_count']}")
        print(f"      traits={m['traitHashes']}")
        print(f"      families={m['activityFamilyHashes']}")


if __name__ == "__main__":
    asyncio.run(main())