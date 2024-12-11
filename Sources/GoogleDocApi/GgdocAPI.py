import datetime
import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
import gspread

from Sources.Utils import Config
from Sources.GoogleDocApi import CellDefines
from Sources.JsonDatabase import JsonDbDefines
from Sources.Utils import WeaponDefinition

SCOPES = ['https://www.googleapis.com/auth/drive']

def OpenGGDoc():
    global spreadsheet
    spreadsheet = ConnectGgdoc()
    global activitySheet
    activitySheet = spreadsheet.worksheet("CurrentActivity")
    UpdateGgDoc(activitySheet)

def GetActivityInformations(activity_name, force_update = True):

    match activity_name:
        case Config.LOSTSECTOR:
            return GetLostSectorInformations(force_update)

def GetLostSectorInformations(force_update = True):

    if(not force_update):
        must_update = MustUpdate(CellDefines.CELL_UPDATE_LOSTSECTOR)
        if(not must_update):
            return False, None

    activity_name = activitySheet.acell(CellDefines.CELL_NAME).value
    activity_hash_expert = activitySheet.acell(CellDefines.CELL_HASH_E).value
    activity_hash_master = activitySheet.acell(CellDefines.CELL_HASH_M).value
    surcharge1 = activitySheet.acell(CellDefines.CELL_SURCHARGE_1).value
    surcharge2 =  activitySheet.acell(CellDefines.CELL_SURCHARGE_2).value
    power_E = int(activitySheet.acell(CellDefines.CELL_POWER_E).value)
    power_M = int(activitySheet.acell(CellDefines.CELL_POWER_M).value)

    champs_E = {}
    champs_M = {}
    shields_E = {}
    shields_M = {}

    champs_E = GetGroupInfos(CellDefines.CELL_CHAMP_E, activitySheet);
    champs_M = GetGroupInfos(CellDefines.CELL_CHAMP_M, activitySheet);
    shields_E = GetGroupInfos(CellDefines.CELL_SHIELD_E, activitySheet);
    shields_M = GetGroupInfos(CellDefines.CELL_SHIELD_M, activitySheet);

    #Weapons
    weapons = {}
    weapon_pool_state = activitySheet.acell(CellDefines.CELL_LS_WEAPON_GROUP).value
    weapons[JsonDbDefines.WEAPONS_STATE] = weapon_pool_state
    if weapons[JsonDbDefines.WEAPONS_STATE] != "Unknown":
        weapons_detail = []
        weapons[JsonDbDefines.WEAPON_FOCUS] = activitySheet.acell(CellDefines.CELL_LS_WEAPON_FOCUS).value
        for weapon_hash_cell in CellDefines.CELL_LS_WEAPONS_HASHES:
            weapon_hash = activitySheet.acell(weapon_hash_cell).value
            weapons_detail.append(WeaponDefinition.GetWeaponsInformations(weapon_hash))
        weapons[JsonDbDefines.WEAPONS_DETAIL] = weapons_detail

    
    #For activities hash you always must have "Expert" and "Master" (you can have only one of them both or none, but your hash can't be smth else) -> See JsonDatabase
    return True, { JsonDbDefines.ACTIVITY_NAME : activity_name, JsonDbDefines.HASH_EXPERT : activity_hash_expert, JsonDbDefines.HASH_MASTER : activity_hash_master
            , JsonDbDefines.SURCHARGE1 : surcharge1, JsonDbDefines.SURCHARGE2 : surcharge2, JsonDbDefines.POWER_EXPERT : power_E, JsonDbDefines.POWER_MASTER : power_M
            , JsonDbDefines.CHAMPS_EXPERT : champs_E, JsonDbDefines.CHAMPS_MASTER : champs_M, JsonDbDefines.SHIELDS_EXPERT : shields_E, JsonDbDefines.SHIELDS_MASTER : shields_M
            , JsonDbDefines.UPDATED : True, JsonDbDefines.WEAPONS : weapons}

def GetGroupInfos(cellDictionnary, sheet):
    ObjectDictionnary = {}
    for object_name, object_cell in cellDictionnary.items():
        raw_cell_value = activitySheet.acell(object_cell).value
        if not isinstance(raw_cell_value, str) or not raw_cell_value.isdigit():
            continue;
        cell_value = int(raw_cell_value)
        if cell_value > 0:
            ObjectDictionnary[object_name] = cell_value
    return ObjectDictionnary

def MustUpdate(cell_name):
    must_update_value = activitySheet.acell(cell_name).value
    return must_update_value == "Yes"

def ConnectGgdoc():
    creds = token()
    
    client = gspread.authorize(creds)
    
    spreadsheet = client.open("Aujourd'hui dans Destiny2")
    
    return spreadsheet

def UpdateGgDoc(sheet):
    #Just for update
    sheet.update_acell(CellDefines.CELL_UPDATE, 'trigger')
    sheet.update_acell(CellDefines.CELL_UPDATE, '')

def token():
    creds = None
    if(os.path.exists(Config.TOKEN_GGDOC)):
        creds = Credentials.from_authorized_user_file(Config.TOKEN_GGDOC, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the token
            creds.refresh(Request())
        else:
            # Else, if the token doesn't exist, get it.
            flow = InstalledAppFlow.from_client_secrets_file(
                Config.CREDENTIALS_GGDOC, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(Config.TOKEN_GGDOC, "w") as token:
            token.write(creds.to_json())
            
    return creds


def GetResetHour():
    spreadsheet = ConnectGgdoc()
    sheet = spreadsheet.worksheet("General Data")
    UpdateGgDoc(sheet)

    hour = (sheet.acell(CellDefines.CELL_HOUR).value).split(":")

    return hour
    
