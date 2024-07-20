from ast import parse
from cgitb import html
from bs4 import BeautifulSoup
import os
import HtmlDefines
import Dictionnary



def CopyTemplate():
    with open(HtmlDefines.TEMPLATE_PATH, 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    with open(HtmlDefines.OUTPUT_PATH, 'w', encoding='utf-8') as file:
        file.write(str(html_file))


def MainInfos(activity_name, background_image, activity_place, activity_destination, rewards):
    with open(HtmlDefines.OUTPUT_PATH, 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')


    ######################################## Main infos #########################################################
    #Get html variables
    html_activity_name = html_file.find(id="activity_name")
    html_activity_place_and_destination = html_file.find(id="activity_description")
    html_activity_background_image = html_file.find(id="sector_background")


    #Fill the html
    if html_activity_name:
        html_activity_name.string = activity_name

    if html_activity_place_and_destination:
        html_activity_place_and_destination.string = activity_place + " - " + activity_destination

    if html_activity_background_image:
        html_activity_background_image['src'] = background_image


    ########################################## Rewards #######################################################
    #Reward names

    span_elements = html_file.find_all('span')

    #Reward 1
    html_reward_1 = html_file.find(id="reward_name_1")
    reward_splitted = TreatRewardText(rewards[0][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_1")
    html_reward_icon_1['src'] = rewards[0][2]

    #Reward 2
    html_reward_1 = html_file.find(id="reward_name_2")
    reward_splitted = TreatRewardText(rewards[1][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_2")
    html_reward_icon_1['src'] = rewards[1][2]

    #Reward 3
    html_reward_1 = html_file.find(id="reward_name_3")
    reward_splitted = TreatRewardText(rewards[2][1])
    parsed_html = BeautifulSoup(reward_splitted[0] + '<br/><span class="small-text">' + reward_splitted[1] + "</span>", 'html.parser')
    html_reward_1.clear()
    html_reward_1.append(parsed_html)

    html_reward_icon_1 = html_file.find(id="reward_icon_3")
    html_reward_icon_1['src'] = rewards[2][2]

    with open(HtmlDefines.OUTPUT_PATH, 'w', encoding='utf-8') as file:
         file.write(str(html_file))
    

def ExpertInfos(power_level, activity_description, damage_breaker_type, modifiers, infos_champ_shield, surcharges):
    with open(HtmlDefines.OUTPUT_PATH, 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    #Power level
    html_power_level = html_file.find(id=HtmlDefines.E_ID_POWER)
    if html_power_level:
        html_power_level.string = str(power_level)

    #Champions
    champions = ParseDescriptionChampions(activity_description)

    champ_container = html_file.find(id="info_champ_container_expert")
    if champ_container:
        champ_container.clear()
        with open(HtmlDefines.T_CHAMP_PATH, 'r', encoding='utf-8') as file:
            txt_champ_template = file.read()

        for champion_type in champions:
            txt_champ_template_copy = txt_champ_template
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampIcon", damage_breaker_type[champion_type])
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampCount", str(infos_champ_shield[0]))
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampType", champion_type)
            champ_container.append(BeautifulSoup(txt_champ_template_copy, 'lxml'))

    #Shields
    boucliers = ParseDescriptionBoucliers(activity_description)

    shield_container = html_file.find(id="info_shield_container_expert")
    if shield_container:
        shield_container.clear()
        with open(HtmlDefines.T_SHIELDS_PATH, 'r', encoding='utf-8') as file:
            txt_shield_template = file.read()
        for champion_type in boucliers:
            txt_shield_copy = txt_shield_template
            txt_shield_copy = txt_shield_copy.replace("ShieldIcon", damage_breaker_type[champion_type])
            txt_shield_copy = txt_shield_copy.replace("ShieldCount", str(infos_champ_shield[1]))
            txt_shield_copy = txt_shield_copy.replace("ShieldType", champion_type)
            shield_container.append(BeautifulSoup(txt_shield_copy, 'lxml'))

    #Modifiers
    modifier_container = html_file.find(id="modifier_section_expert")
    if modifier_container:
        modifier_container.clear()
        with open(HtmlDefines.T_MODIFIER_PATH, 'r', encoding='utf-8') as file:
            txt_modifier_template = file.read()
        for modifier in modifiers:
            txt_modifier_copy = txt_modifier_template
            txt_modifier_copy = txt_modifier_copy.replace("ModifierIcon", modifier[3])
            txt_modifier_copy = txt_modifier_copy.replace("ModifierName", modifier[1])
            txt_modifier_copy = txt_modifier_copy.replace("ModifierDescription", modifier[2])
            modifier_container.append(BeautifulSoup(txt_modifier_copy, 'lxml'))
            

    with open(HtmlDefines.OUTPUT_PATH, 'w', encoding='utf-8') as file:
         file.write(str(html_file))

def MaitriseInfos(power_level, activity_description, damage_breaker_type, modifiers, infos_champ_shield, surcharges):
    with open(HtmlDefines.OUTPUT_PATH, 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    #Power level
    html_power_level = html_file.find(id=HtmlDefines.M_ID_POWER)
    if html_power_level:
        html_power_level.string = str(power_level)

    #Champions
    champions = ParseDescriptionChampions(activity_description)

    champ_container = html_file.find(id="info_champ_container_master")
    if champ_container:
        champ_container.clear()
        with open(HtmlDefines.T_CHAMP_PATH, 'r', encoding='utf-8') as file:
            txt_champ_template = file.read()

        for champion_type in champions:
            txt_champ_copy = txt_champ_template
            txt_champ_copy = txt_champ_copy.replace("ChampIcon", damage_breaker_type[champion_type])
            txt_champ_copy = txt_champ_copy.replace("ChampCount", str(infos_champ_shield[0]))
            txt_champ_copy = txt_champ_copy.replace("ChampType", champion_type)
            champ_container.append(BeautifulSoup(txt_champ_copy, 'lxml'))

    #Shields
    boucliers = ParseDescriptionBoucliers(activity_description)

    shield_container = html_file.find(id="info_shield_container_master")
    if shield_container:
        shield_container.clear()
        with open(HtmlDefines.T_SHIELDS_PATH, 'r', encoding='utf-8') as file:
            txt_shield_template = file.read()
        for champion_type in boucliers:
            txt_shield_template_copy = txt_shield_template
            txt_shield_template_copy = txt_shield_template_copy.replace("ShieldIcon", damage_breaker_type[champion_type])
            txt_shield_template_copy = txt_shield_template_copy.replace("ShieldCount", str(infos_champ_shield[1]))
            txt_shield_template_copy = txt_shield_template_copy.replace("ShieldType", champion_type)
            shield_container.append(BeautifulSoup(txt_shield_template_copy, 'lxml'))

    #Modifiers
    modifier_container = html_file.find(id="modifier_section_master")
    if modifier_container:
        modifier_container.clear()
        with open(HtmlDefines.T_MODIFIER_PATH, 'r', encoding='utf-8') as file:
            txt_modifier_template = file.read()
        for modifier in modifiers:
            txt_modifier_copy = txt_modifier_template
            txt_modifier_copy = txt_modifier_copy.replace("ModifierIcon", modifier[3])
            txt_modifier_copy = txt_modifier_copy.replace("ModifierName", modifier[1])
            txt_modifier_copy = txt_modifier_copy.replace("ModifierDescription", modifier[2])
            modifier_container.append(BeautifulSoup(txt_modifier_copy, 'lxml'))

    with open(HtmlDefines.OUTPUT_PATH, 'w', encoding='utf-8') as file:
         file.write(str(html_file))

def ParseDescriptionChampions(description):
    champions = []
    champions_line, _ = ExtraireText(description, "Champions", "Menace")
    for i in range(10): #Artificil end
        type, champions_line = ExtraireText(champions_line, "[", "]")
        if type == None:
            break
        if type in Dictionnary.BREAKER_TYPES:
            champions.append(type)
        elif type in Dictionnary.BREAKER_TRANSLATION:
            champions.append(Dictionnary.BREAKER_TRANSLATION[type])

    return champions

def ParseDescriptionBoucliers(description):
    boucliers = []
    bouclier_line, _ = ExtraireText(description, "Boucliers", "Modificateurs")
    for i in range(10): #Artificil end
        type, bouclier_line = ExtraireText(bouclier_line, "[", "]")
        if type == None:
            break
        if type in Dictionnary.DAMAGE_TYPES:
            boucliers.append(type)
        elif type in Dictionnary.DAMAGE_TRANSLATION:
            boucliers.append(Dictionnary.DAMAGE_TRANSLATION[type])

    return boucliers


def ExtraireText(chaine, debut, fin):
    debut_index = chaine.find(debut) + len(debut)
    fin_index = chaine.find(fin, debut_index)
    if debut_index == -1 or fin_index == -1:
        return None
    return chaine[debut_index:fin_index], chaine[fin_index:]
    

def TreatRewardText(reward_text):
    reward_text = reward_text.replace("En solo - ", "")

    name_rarity_split = reward_text.split(" (")
    name = name_rarity_split[0].replace(" ", "<br/>")
    rarity = "(" + name_rarity_split[1]
    
    return [name, rarity]
