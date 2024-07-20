import Config
import csv

CSV_DATE = 0
CSV_NAME = 1
CSV_POWER_EXPERT = 2
CSV_POWER_MAITRISE = 3
CSV_NV_CHAMP_EXPERT = 4
CSV_NV_SHIELD_EXPERT = 5
CSV_NV_CHAMP_MAITRISE = 6
CSV_NV_SHIELD_MAITRISE = 7
CSV_SURCHARGE1 = 8
CSV_SURCHARGE2 = 9



def ReadCsv():

	with open(Config.CSV_FILENAME, "r") as file:
		reader = csv.reader(file)

		for row in reader:
			if(row[CSV_DATE] == "Test"):
				return (row[CSV_NAME], 
						row[CSV_POWER_EXPERT], 
						row[CSV_POWER_MAITRISE],
						row[CSV_NV_CHAMP_EXPERT],
						row[CSV_NV_SHIELD_EXPERT],
						row[CSV_NV_CHAMP_MAITRISE],
						row[CSV_NV_SHIELD_MAITRISE],
						row[CSV_SURCHARGE1],
						row[CSV_SURCHARGE2])

