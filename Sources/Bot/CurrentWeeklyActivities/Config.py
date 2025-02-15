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


OBJECTIVE_DUNGEON_HASH = ["2697564403", "1283234589"]
OBJECTIVE_RAID_HASH = "406803827"
OBJECTIVE_EXOMISSION_HASH = "3726310377"
OBJECTIVE_NN_HASH = "1612424695"