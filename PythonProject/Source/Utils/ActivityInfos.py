ACTIVITY_NAME = "NONE"
POWER_E = "NONE"
POWER_M = "NONE"
SURCHARGES = "NONE"
SHIELDS_E = "NONE"
SHIELDS_M = "NONE"
CHAMPS_E = "NONE"
CHAMPS_M = "NONE"

def SetActivityName(aActivityName):
    global ACTIVITY_NAME
    ACTIVITY_NAME = aActivityName
    
def SetPower(aExpert, aPower):
    if(aExpert):
        global POWER_E
        POWER_E = aPower
    else:
        global POWER_M
        POWER_M = aPower
        
def SetSurcharges(aSurcharges):
    global SURCHARGES
    SURCHARGES = aSurcharges
    
def SetShields(aExpert, aShields):
    if(aExpert):
        global SHIELDS_E
        SHIELDS_E = aShields
    else:
        global SHIELDS_M
        SHIELDS_M = aShields
    
def SetChamps(aExpert, aChamps):
    if(aExpert):
        global CHAMPS_E
        CHAMPS_E = aChamps
    else:
        global CHAMPS_M
        CHAMPS_M = aChamps

def GetActivityName():
    return ACTIVITY_NAME

def GetPower(aExpert):
    if(aExpert):
        return POWER_E
    else:
        return POWER_M
    
def GetSurcharges():
    return SURCHARGES

def GetShields(aExpert):
    if(aExpert):
        return SHIELDS_E
    else:
        return SHIELDS_M
    
def GetChamps(aExpert):
    if(aExpert):
        return CHAMPS_E
    else:
        return CHAMPS_M


