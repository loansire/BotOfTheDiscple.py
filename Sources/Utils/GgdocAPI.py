import datetime
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread

from Sources.Utils import Config
from Sources.Utils import CellDefines

SCOPES = ['https://www.googleapis.com/auth/drive']


def main():
    
    spreadsheet = ConnectGgdoc()
    sheet = spreadsheet.get_worksheet(2)
    UpdateGgDoc(sheet)
    
    #Get infos
    activity_name = sheet.acell(CellDefines.CELL_NAME).value
    surcharge1 = sheet.acell(CellDefines.CELL_SURCHARGE_1).value
    surcharge2 =  sheet.acell(CellDefines.CELL_SURCHARGE_2).value
    power_E = int(sheet.acell(CellDefines.CELL_POWER_E).value)
    power_M = int(sheet.acell(CellDefines.CELL_POWER_M).value)
    
    champs_E = {}
    champs_M = {}
    shields_E = {}
    shields_M = {}
    
    for champ_name, champ_cell in CellDefines.CELL_CHAMP_E.items():
        raw_cell_value = sheet.acell(champ_cell).value
        if not isinstance(raw_cell_value, str) or not raw_cell_value.isdigit():
            continue;
        cell_value = int(raw_cell_value)
        if cell_value > 0:
            champs_E[champ_name] = cell_value
            
    for champ_name, champ_cell in CellDefines.CELL_CHAMP_M.items():
        raw_cell_value = sheet.acell(champ_cell).value
        if not isinstance(raw_cell_value, str) or not raw_cell_value.isdigit():
            continue;
        cell_value = int(raw_cell_value)
        if cell_value > 0:
            champs_M[champ_name] = cell_value
            
    for shield_name, shield_cell in CellDefines.CELL_SHIELD_E.items():
        raw_cell_value = sheet.acell(shield_cell).value
        if not isinstance(raw_cell_value, str) or not raw_cell_value.isdigit():
            continue;
        cell_value = int(raw_cell_value)
        if cell_value > 0:
            shields_E[shield_name] = cell_value
                
    for shield_name, shield_cell in CellDefines.CELL_SHIELD_M.items():
        raw_cell_value = sheet.acell(shield_cell).value
        if not isinstance(raw_cell_value, str) or not raw_cell_value.isdigit():
            continue;
        cell_value = int(raw_cell_value)
        if cell_value > 0:
            shields_M[shield_name] = cell_value


    return activity_name, surcharge1, surcharge2, power_E, power_M, shields_E, shields_M, champs_E, champs_M 

def ConnectGgdoc():
    creds = token()
    
    client = gspread.authorize(creds)
    
    spreadsheet = client.open("LostSectorDatabase")
    
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
            creds.refresh(Request())
            
        else:
            flow = InstalledAppFlow.from_client_secrets_file(Config.CREDENTIALS_GGDOC, SCOPES)
            creds = flow.run_console()
        with open(Config.TOKEN_GGDOC, "w") as token:
            token.write(creds.to_json())
            
    return creds

def GetResetHour():
    spreadsheet = ConnectGgdoc()
    sheet = spreadsheet.get_worksheet(0  )
    UpdateGgDoc(sheet)
    
    hour = (sheet.acell(CellDefines.CELL_HOUR).value).split(":")
    
    return hour
    
