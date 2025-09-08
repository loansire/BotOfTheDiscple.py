from dataclasses import dataclass, field

DEFINITION = [
    "DestinyActivityDefinition",
    "DestinyActivityInteractableDefinition",
    "DestinyDestinationDefinition",
    "DestinyPlaceDefinition",
    "DestinyActivityGraphDefinition",
    "DestinyInventoryItemDefinition",
    "DestinyActivityModifierDefinition",
    "DestinyCollectibleDefinition",

    #============ WebSite ============#
    "DestinySandboxPerkDefinition",
    "DestinyEquipableItemSetDefinition",
    "DestinyCollectibleDefinition",
    "DestinyPlugSetDefinition"
]

@dataclass
class DestinyActivityDefinition:
    hash: int
    activityTypeHash: int
    display_name: str = ""
    display_description: str = ""
    display_icon: str = ""
    original_name: str = ""
    original_description: str = ""
    original_icon: str = ""
    releaseIcon: str = ""
    activityLightLevel: int = -1
    destinationHash: int = -1 #Hash to DestinyDestinationDefinition
    placeHash: int = -1 #Hash to DestinyPlaceDefinition
    pgcrImage: str = ""
    rewards: list[int] = field(default_factory=list) #Hash to DestinyInventoryItemDefinition
    modifierHashes: list[int] = field(default_factory=list) #Hash to DestinyActivityModifierDefinition

@dataclass
class DestinyActivityInteractableDefinition:
    hash: int
    activity_hashes: list[int] = field(default_factory=list) #Hash to DestinyActivityDefinition

@dataclass
class DestinyDestinationDefinition:
    hash: int
    name: str = ""
    description: str = ""
    placeHash: int = -1 #Hash to DestinyPlaceDefinition

@dataclass
class DestinyPlaceDefinition:
    hash: int
    name: str = ""
    description: str = ""

@dataclass
class DestinyActivityGraphDefinition:
    hash: int
    node_name: str = ""
    node_description: str = ""
    activityHash: list[int] = field(default_factory=list) #Hash to DestinyActivityDefinition

@dataclass
class DestinyInventoryItemDefinition:
    hash: int
    description: str = ""
    name: str = ""
    collectibleHash: int = -1 #Hash to DestinyCollectibleDefinition
    icon: str = ""
    iconWatermark: str = ""
    iconWatermarkFeatured: str = ""
    isFeaturedItem: str = ""
    screenshot: str = ""
    itemTypeDisplayName: str = ""

    #socketTypeHash: int = -1 # ??
    #singleInitialItemHash: int = 0 #Hash to DestinyInventoryItemDefinition
    #randomizedPlugSetHash: int = -1 #Hash to DestinyPlugSetDefinition


@dataclass
class DestinyActivityModifierDefinition:
    hash: int
    description: str = ""
    name: str = ""
    icon: str = ""
    icon_1: str = ""
    icon_2: str = ""

"""
@dataclass
class DestinySandboxPerkDefinition:
    hash: int

@dataclass
class DestinyEquipableItemSetDefinition:
    hash: int
    
@dataclass
class DestinyCollectibleDefinition:
    hash: int
    name: str = ""
    icon: str = ""
    sourceString: str = ""
    itemHash: int = -1 #Hash to DestinyInventoryItemDefinition
    
@dataclass
class DestinyPlugSetDefinition:
    hash: int
    plugItemHash: int = -1 #Hash to DestinyInventoryItemDefinition
"""
