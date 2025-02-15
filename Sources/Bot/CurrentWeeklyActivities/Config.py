MF_ACTIVITY_DEFINITION = "DestinyActivityDefinition"
MF_ACTIVITY_TYPE_DEFINITION = "DestinyActivityTypeDefinition"
MF_MODIFIER_DEFINITION = "DestinyActivityModifierDefinition"
MF_OBJECTIVE_DEFINITION = "DestinyObjectiveDefinition"


FIELDTODELET = [
    'isNew', 'canLead', 'canJoin', 'isCompleted',
    'isVisible', 'displayLevel', 'recommendedLight', 'difficultyTier',
    'complete', 'visible', 'activityLightLevel',
    'challenges.objective.activityHash',
    'challenges.objective.progress',
    'challenges.objective.completionValue',
    'challenges.objective.complete',
    'challenges.objective.visible',
]


ACTIVITY_FIELDS = [
    "displayProperties.name",
    "activityTypeHash",
    "originalDisplayProperties.name",
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


DUNGEON_TYPE_HASH = "608898761"
RAID_TYPE_HASH = "2043403989"

OBJECTIVE_DUNGEON_HASHE = ""
OBJECTIVE_RAID_HASHE = ""
OBJECTIVE_EXOMISSION_HASHE = ""
OBJECTIVE_GM_HASHE = ""