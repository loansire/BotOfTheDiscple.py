# -*- coding: utf-8 -*-
import sys
import os

from Sources.LostSector.LostSectorGenerator import GenerateActivity, GetActivityName, GetPower, GetShields, GetChamps, GetSurcharges

def main():
    
    #On demande des infos non créés !!! (Tout renvoie "NONE")
    if GetPower(True) == "NONE":
        print("MY POWER IS UNLIMITED (means no power :) )")

    GenerateActivity()

    #ActivityName
    print("Activity is :" + GetActivityName())
    
    #Powers
    print("Expert Power is : " + str(GetPower(True))) # Faut mettre True pour expert et False pour Maitrise
    print("Maitrise Power is : " + str(GetPower(False)))
     
    #Surcharge
    surcharges = GetSurcharges()
    for surcharge in surcharges:
        print("Il y a la surcharge " + surcharge)
        
    #Shields expert
    for shield, number in GetShields(True).items():
        print("Il y a " + str(number) + " shield expert de type " + shield)
    #Shields Maitrise    
    for shield, number in GetShields(False).items():
        print("Il y a " + str(number) + " shield maitrise de type " + shield)
        
    #Champs expert
    for champ, number in GetChamps(True).items():
        print("Il y a " + str(number) + " champ expert de type " + champ)
    #Champs Maitrise    
    for champ, number in GetChamps(False).items():
        print("Il y a " + str(number) + " champ maitrise de type " + champ)


if __name__ == "__main__":
    main()