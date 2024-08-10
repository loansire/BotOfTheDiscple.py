import html
from bs4 import BeautifulSoup

from Html import HtmlDefines
from Utils import Dictionnary
from Utils import Config
from Utils import HTMLToPNG



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
    

def SpecificInfos(power_level, shield_count, champ_count, icons_infos, modifiers, is_expert = True):
    with open(HtmlDefines.OUTPUT_PATH, 'r', encoding='utf-8') as file:
        html_file = BeautifulSoup(file, 'lxml')

    #Power level
    if is_expert:
        html_power_level = html_file.find(id=HtmlDefines.E_ID_POWER)
    else:
        html_power_level = html_file.find(id=HtmlDefines.M_ID_POWER)
    if html_power_level:
        html_power_level.string = str(power_level)

    if is_expert:
        container_name = "info_champ_container_expert"
    else:
        container_name = "info_champ_container_master"

    champ_container = html_file.find(id=container_name)
    if champ_container:
        champ_container.clear()
        with open(HtmlDefines.T_CHAMP_PATH, 'r', encoding='utf-8') as file:
            txt_champ_template = file.read()

        for champion_type in champ_count.keys():
            if champion_type in Dictionnary.FINAL_TRANSLATIONS.keys():
                final_translation = Dictionnary.FINAL_TRANSLATIONS[champion_type]
            else:
                final_translation = champion_type
            txt_champ_template_copy = txt_champ_template
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampIcon", icons_infos[champion_type])
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampCount", str(champ_count[champion_type]))
            txt_champ_template_copy = txt_champ_template_copy.replace("ChampType", final_translation)
            champ_container.append(BeautifulSoup(txt_champ_template_copy, 'lxml'))

    
    if is_expert:
        container_name = "info_shield_container_expert"
    else:
        container_name = "info_shield_container_master"

    shield_container = html_file.find(id=container_name)
    if shield_container:
        shield_container.clear()
        with open(HtmlDefines.T_SHIELDS_PATH, 'r', encoding='utf-8') as file:
            txt_shield_template = file.read()
        for shield_type in shield_count.keys():
            if shield_type in Dictionnary.FINAL_TRANSLATIONS.keys():
                final_translation = Dictionnary.FINAL_TRANSLATIONS[shield_type]
            else:
                final_translation = shield_type
            txt_shield_copy = txt_shield_template
            txt_shield_copy = txt_shield_copy.replace("ShieldIcon", icons_infos[shield_type])
            txt_shield_copy = txt_shield_copy.replace("ShieldCount", str(shield_count[shield_type]))
            txt_shield_copy = txt_shield_copy.replace("ShieldType", final_translation)
            shield_container.append(BeautifulSoup(txt_shield_copy, 'lxml'))

    #Modifiers
    if is_expert:
        container_name = "modifier_section_expert"
    else:
        container_name = "modifier_section_master"
    modifier_container = html_file.find(id=container_name)
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

def TreatRewardText(reward_text):
    reward_text = reward_text.replace("En solo - ", "")

    name_rarity_split = reward_text.split(" (")
    name = name_rarity_split[0].replace(" ", "<br/>")
    rarity = "(" + name_rarity_split[1]
    
    return [name, rarity]

def ConvertToJpeg():
    HTMLToPNG.html_to_png(HtmlDefines.OUTPUT_PATH, HtmlDefines.OUTPUT_JPEG_PATH)
