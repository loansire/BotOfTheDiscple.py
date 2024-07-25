from enum import Enum
import Dictionnary

class Surcharge(Enum):
    Cryo = 1
    Abyssal = 2
    Solaire = 3
    Filobscure = 4
    Stasique = 5


#Definitions
modifier_ban_list = {"Champions adverses", "Ennemis avec bouclier", "Équipement verrouillé"}
ARMES_SURCHARGEES = "Armes surchargées"
variables_replace = {"{var:4005007457}" : "25", "{var:2189146210}" : "25", "{var:1027206613}" : "25"}
surcharges_possible = {Surcharge.Cryo : "Surcharge cryo-électrique", Surcharge.Solaire : "Surcharge solaire", Surcharge.Abyssal :"Surcharge abyssale", Surcharge.Filobscure : "Surcharge filobscure", Surcharge.Stasique : "Surcharge stasique"}


def ClearModifiers(modifiers, list_surcharge):
    change = False
    for i in range(len(modifiers) -1 , -1, -1):
        change = False
        modifier = modifiers[i]

        modifier = (modifier[0], modifier[1], ReplaceVariables(modifier[2]), modifier[3])
        #Remove useless stuff
        if modifier[1] == "" or modifier[1] in modifier_ban_list:
            del modifiers[i]
            continue

        #Armes surchargées
        if modifier[1] == ARMES_SURCHARGEES:
            modifier_split = modifier[2].split("\n")
            modifier = (modifier[0], modifier[1], modifier_split[2], modifier[3])

        for key, value in surcharges_possible.items():
            if modifier[1] == value and key not in list_surcharge:
                del modifiers[i]
                change = True
                break


        if not change:
            modifiers[i] = modifier
    return modifiers


def ReplaceVariables(modifier_description):
    for key, value in variables_replace.items():
        modifier_description = modifier_description.replace(key, value)
    return modifier_description


def TranslateSurcharge(surcharge_str):
    if surcharge_str in Dictionnary.SURCHARGE_TRANSLATION.keys():
        surcharge_str = Dictionnary.SURCHARGE_TRANSLATION[surcharge_str]
    surcharge_enum = Surcharge.Solaire
    match surcharge_str:
        case "Stase":
            surcharge_enum = Surcharge.Stasique
        case "Filobscur":
            surcharge_enum = Surcharge.Filobscure
        case "Solaires":
            surcharge_enum = Surcharge.Solaire
        case "Cryo-électriques":
            surcharge_enum = Surcharge.Cryo
        case "Abyssaux":
            surcharge_enum = Surcharge.Abyssal

    return surcharge_enum


