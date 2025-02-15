MF_ACTIVITY_DEFINITION = "DestinyActivityDefinition"
MF_ACTIVITY_TYPE_DEFINITION = "DestinyActivityTypeDefinition"
MF_MODIFIER_DEFINITION = "DestinyActivityModifierDefinition"
MF_OBJECTIVE_DEFINITION = "DestinyObjectiveDefinition"


FIELDTODELET = [
    'isNew', 'canLead', 'canJoin',
    'isCompleted', 'isVisible', 'displayLevel',
    'recommendedLight', 'difficultyTier', 'complete',
    'visible', 'activityLightLevel',
    'challenges.objective.activityHash',
    'challenges.objective.progress',
    'challenges.objective.completionValue',
    'challenges.objective.complete',
    'challenges.objective.visible',
]

MODIFIERTODELET = {
    # Vide
    1783825372,
    # Ennemis avec bouclier
    2833087500, 1553093202, 2833087500,
    3139381566, 3230561446, 3538098588,
    3958417570, 1651706850,
    # Modificateur de difficulté
    85104725, 1174869237, 3674616727,
    445825536, 2001067135, 3897480986,
    501815068, 2567927655, 4087563963,
    791047754, 3240131679, 1139702033,
    3623371497,
    # Champions adverses
    2006149364, 438106166, 1262171714,
    1990363418, 2006149364, 2475764450,
    3307318061, 4190795159,
}

ACTIVITY_FIELDS = [
    "displayProperties.name",
    "activityTypeHash",
    "originalDisplayProperties.name",
    "displayProperties.description",
    "pgcrImage",
]
ACTIVITY_TYPE_FIELDS = [
    "displayProperties.name",
]
MODIFIER_FIELDS = [
    "displayProperties.name",
    "displayProperties.icon",
    "displayProperties.description",
]
OBJECTIVE_FIELDS = [
    "displayProperties.name",
]

# Défi de donjon hebdomadaire
OBJECTIVE_DUNGEON_HASH = [
    "1062014463", "2367956143", "2697564403",
    "1283234589", "3039545165", "1288508599",
    "2039792527", "3211393925", "3838169295",
]
# Défi de Raid de la semaine
OBJECTIVE_RAID_HASH = [
    "406803827", "897950155", "1633394671",
    "1863972407", "2398860795", "3180884403",
    "3767289993", "3826130187",
]
# Défi de rotation exotique hebdomadaire
OBJECTIVE_EXOMISSION_HASH = [
    "3726310377", "1510063869", "1274811193",
    "1320261963", "3407714741",
]
# Défi de score de la semaine
OBJECTIVE_NN_HASH = ["1612424695"]