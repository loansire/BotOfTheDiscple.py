
# \Configuration des Key-value et des Definitions\

"""
  DEFINITION :list
              nom des local_definitions à télécharger et à update.
  KEY_MAP :dict
              associe des clefs d'objet JSON à un manifest.
  ACTIVITI_TYPE_MAP :dict
              liste les potentiels Filtres à garder pour trier les types d'activités.
"""

KEY_MAP = {
    "activityHash":"DestinyActivityDefinition",
    "itemHash":"DestinyInventoryItemDefinition",
    "modifierHashes":"DestinyActivityModifierDefinition",
    "activityInteractableHash":"DestinyActivityInteractableDefinition",
    "destinationHash":"DestinyDestinationDefinition",
    "placeHash":"DestinyPlaceDefinition",
    "activityModifierHash":"DestinyActivityModifierDefinition",
    "activityTypeHash":"DestinyActivityTypeDefinition",
}

ACTIVITI_TYPE_MAP = {
  "SoloOps": 3851289711,  # Hash des types "SoloOps"
  "ExoticMission": 1227821118,  # Hash des types "ExoticMission" (Opération prestige)
  "Raid": 2043403989,  # Hash des types "Raid"
  "Donjon": 608898761,   # Hash des types "Donjon"
  "Story": 1686739444,  # Hash des types "Story" (pour exotic mission, enrichi avec EXOTIC_DEFINITION)
  "LostSector": 103143560,   # Hash des types "LostSector"
}

ACTIVITI_GRAPH_MAP = {
  "FireteamOps": 2021988413,
  "SoloOps": 1733518967,
  "PinnacleOps": 2427019152,
  "LegendsNode": 1148849101,
  "CrussibleOps": 3557894678,
}

ACTIVITI_LINK_MAP = {
    # ceux qui se résolvent via GRAPH
    "FireteamOps": ("graph", "FireteamOps"),
    "SoloOps": ("graph", "SoloOps"),
    "PinnacleOps": ("graph", "PinnacleOps"),
    "CrussibleOps": ("graph", "CrussibleOps"),
    "LegendsNode": ("graph", "LegendsNode"),

    # ceux qui se résolvent via TYPE
    "Raid": ("type", "Raid"),
    "Donjon": ("type", "Donjon"),
    "LostSector": ("type", "LostSector"),
}
