from tkinter.tix import COLUMN
import Config
import csv
import pandas as pd
import Dictionnary

sheet_id = '1yzlUK5dlqhSg0ZGQ79o-4n9j2mRZiFgECi1CBI1Ht1I'
page_id_db = 0
page_id_current = 1205713815

LostSector_csv_line = {}

def ReadGGDocActivity():
	global LostSector_csv_line
	activity_name = "Jardin de l'Exode 2A"
	surcharge1 = "Abyssal"
	surcharge2 = "Solaires"
	try:
		LostSector_csv_line = pd.read_csv("https://docs.google.com/spreadsheets/d/" + sheet_id + "/export?gid=" + str(page_id_current) + "&format=csv")
		activity_name = LostSector_csv_line.loc[0, "Nom"]
		surcharge1 = LostSector_csv_line.loc[0, "Surcharge1"]
		surcharge2 = LostSector_csv_line.loc[0, "Surcharge2"]




	except:
		print("Can't access ggdoc infos. Using Defaults values")


	return activity_name, surcharge1, surcharge2

def GetExpertPower():
	return int(LostSector_csv_line.iloc[0]['Power Expert'])


def GetMaitrisePower():
	return int(LostSector_csv_line.iloc[0]['Power Maitrise'])

def GetInfosTypes(is_expert = True, is_shield = True):
	if is_expert:
		str_diff = "Expert "
	else:
		str_diff = "Maitrise "

	types = {}
	
	if is_shield:
		print("Finding types for Shields for " + str_diff)
		container = Dictionnary.DAMAGE_TYPES
	else:
		print("Finding types for Champs for " + str_diff)
		container = Dictionnary.BREAKER_TYPES

	for type in container:
		column_name = str_diff + type
		try:
			type_count = LostSector_csv_line[column_name].values[0]
		except KeyError as e:
			print("Column : " + column_name + " is not in the table")
			continue

		if pd.isna(type_count) or type_count == 0:
			continue
		
		types[type] = int(type_count)

	return types

def GetChampsTypes(is_expert = True):
	if is_expert:
		str_diff = "Expert "
	else:
		str_diff = "Maitrise "

	types = {}
	
	for type in Dictionnary.BREAKER_TYPES:
		column_name = str_diff + type
		try:
			type_count = LostSector_csv_line[column_name].values[0]
		except KeyError as e:
			print("Column : " + column_name + " is not in the table")
			continue

		if pd.isna(type_count) or type_count == 0:
			continue
		
		types[type] = int(type_count)

	return types

